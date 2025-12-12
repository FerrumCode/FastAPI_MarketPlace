from __future__ import annotations

import logging
import asyncio
from decimal import Decimal, ROUND_HALF_UP

from prometheus_client import Counter, Histogram
from app.celery_app import celery_app
from app.schemas import KafkaOrderEvent, FinalOrderItemPatch, FinalOrderPatch
from app.services.exchange import get_exchange_rate
from app.services.shipping import calculate_delivery
from app.services.orders_repo import patch_final_order
from env import DEFAULT_TARGET_CURRENCY, SERVICE_NAME

logger = logging.getLogger(__name__)


ORDERS_TASK_RUNS_TOTAL = Counter(
    "celery_worker_orders_task_runs_total",
    "Number of times orders.process_order_created task was invoked",
    ["service"],
)

ORDERS_TASK_RESULTS_TOTAL = Counter(
    "celery_worker_orders_task_results_total",
    "Results of orders.process_order_created task",
    ["service", "result"],
)

ORDERS_TASK_RETRIES_TOTAL = Counter(
    "celery_worker_orders_task_retries_total",
    "Retries requested by orders.process_order_created task",
    ["service", "reason"],
)


ORDERS_TASK_ERRORS_TOTAL = Counter(
    "celery_worker_orders_task_errors_total",
    "Errors in orders.process_order_created task by type",
    ["service", "error_type"],
)


ORDERS_CART_PRICE_RUB = Histogram(
    "celery_worker_orders_cart_price_rub",
    "Calculated cart price (RUB) in orders.process_order_created",
    ["service"],
)

ORDERS_DELIVERY_PRICE_RUB = Histogram(
    "celery_worker_orders_delivery_price_rub",
    "Calculated delivery price (RUB) in orders.process_order_created",
    ["service"],
)

ORDERS_TOTAL_PRICE_RUB = Histogram(
    "celery_worker_orders_total_price_rub",
    "Calculated total price (RUB) in orders.process_order_created",
    ["service"],
)

ORDERS_TOTAL_QUANTITY = Histogram(
    "celery_worker_orders_total_quantity",
    "Total item quantity in orders.process_order_created",
    ["service"],
)

ORDERS_ITEMS_COUNT = Histogram(
    "celery_worker_orders_items_count",
    "Number of distinct items in ORDER_CREATED event",
    ["service"],
)


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@celery_app.task(
    bind=True,
    name="orders.process_order_created",
    max_retries=5,
    default_retry_delay=60,
)
def process_order_created(self, event_payload: dict) -> None:
    ORDERS_TASK_RUNS_TOTAL.labels(service=SERVICE_NAME).inc()

    try:
        event = KafkaOrderEvent.model_validate(event_payload)
    except Exception as exc:
        logger.exception("Failed to validate Kafka ORDER_CREATED event: %s", exc)
        ORDERS_TASK_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            error_type="validation_error",
        ).inc()
        ORDERS_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="validation_error",
        ).inc()
        return

    if event.event != "ORDER_CREATED":
        logger.info(
            "process_order_created called for non ORDER_CREATED event (%s), ignoring",
            event.event,
        )

        ORDERS_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="ignored",
        ).inc()

        return

    base_currency = event.currency_base.upper()
    target_currency = DEFAULT_TARGET_CURRENCY.upper()
    order_id_str = str(event.order_id)

    try:
        rate = get_exchange_rate(base_currency, target_currency)
    except Exception as exc:
        ORDERS_TASK_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            error_type="exchange_rate_error",
        ).inc()
        ORDERS_TASK_RETRIES_TOTAL.labels(
            service=SERVICE_NAME,
            reason="exchange_rate_error",
        ).inc()
        ORDERS_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="retry_exchange_rate_error",
        ).inc()
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

    ORDERS_CART_PRICE_RUB.labels(service=SERVICE_NAME).observe(float(cart_rub))
    ORDERS_DELIVERY_PRICE_RUB.labels(service=SERVICE_NAME).observe(float(delivery_rub))
    ORDERS_TOTAL_PRICE_RUB.labels(service=SERVICE_NAME).observe(float(total_rub))
    ORDERS_TOTAL_QUANTITY.labels(service=SERVICE_NAME).observe(float(total_quantity))
    ORDERS_ITEMS_COUNT.labels(service=SERVICE_NAME).observe(float(len(event.items)))

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
        ORDERS_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="success",
        ).inc()
    except Exception as exc:
        ORDERS_TASK_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            error_type="orders_service_patch_error",
        ).inc()
        ORDERS_TASK_RETRIES_TOTAL.labels(
            service=SERVICE_NAME,
            reason="orders_service_patch_error",
        ).inc()
        ORDERS_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="retry_orders_service_patch_error",
        ).inc()
        logger.exception(
            "Failed to patch order %s via Orders Service, "
            "retrying (attempt %s of %s): %s",
            order_id_str,
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        raise self.retry(exc=exc)
