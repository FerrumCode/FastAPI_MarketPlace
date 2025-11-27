from __future__ import annotations

import logging
import asyncio
from decimal import Decimal, ROUND_HALF_UP

from app.celery_app import celery_app
from app.schemas import KafkaOrderEvent, FinalOrderItemPatch, FinalOrderPatch
from app.services.exchange import get_exchange_rate
from app.services.shipping import calculate_delivery
from app.services.orders_repo import patch_final_order
from env import DEFAULT_TARGET_CURRENCY

logger = logging.getLogger(__name__)


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@celery_app.task(
    bind=True,
    name="orders.process_order_created",
    max_retries=5,
    default_retry_delay=60,
)
def process_order_created(self, event_payload: dict) -> None:
    try:
        event = KafkaOrderEvent.model_validate(event_payload)
    except Exception as exc:
        logger.exception("Failed to validate Kafka ORDER_CREATED event: %s", exc)
        return

    if event.event != "ORDER_CREATED":
        logger.info(
            "process_order_created called for non ORDER_CREATED event (%s), ignoring",
            event.event,
        )
        return

    base_currency = event.currency_base.upper()
    target_currency = DEFAULT_TARGET_CURRENCY.upper()
    order_id_str = str(event.order_id)

    try:
        rate = get_exchange_rate(base_currency, target_currency)
    except Exception as exc:
        logger.exception(
            "Failed to get exchange rate %s->%s for order %s, "
            "retrying (attempt %s of %s): %s",
            base_currency,
            target_currency,
            order_id_str,
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        raise self.retry(exc=exc)

    total_quantity = 0
    patched_items: list[FinalOrderItemPatch] = []
    cart_rub = Decimal("0.00")

    for item in event.items:
        total_quantity += int(item.quantity)
        price_base = Decimal(str(item.unit_price))
        price_rub = _money(price_base * rate)
        cart_rub += price_rub * int(item.quantity)

        patched_items.append(
            FinalOrderItemPatch(
                product_id=item.product_id,
                unit_price=price_rub,
            )
        )

    delivery_rub = calculate_delivery(cart_rub, total_quantity)
    total_rub = cart_rub + delivery_rub

    patch = FinalOrderPatch(
        cart_price=cart_rub,
        delivery_price=delivery_rub,
        total_price=total_rub,
        items=patched_items,
    )

    try:
        updated = asyncio.run(patch_final_order(order_id_str, patch))
        logger.info(
            "Order %s updated via Orders Service: cart=%s, delivery=%s, total=%s, status=%s",
            updated.id,
            updated.cart_price,
            updated.delivery_price,
            updated.total_price,
            updated.status,
        )
    except Exception as exc:
        logger.exception(
            "Failed to patch order %s via Orders Service, "
            "retrying (attempt %s of %s): %s",
            order_id_str,
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        raise self.retry(exc=exc)
