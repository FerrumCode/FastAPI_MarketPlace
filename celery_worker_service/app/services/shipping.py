from decimal import Decimal, ROUND_HALF_UP

from loguru import logger

from env import SERVICE_NAME
from app.core.metrics import DELIVERY_CALCULATIONS_TOTAL, DELIVERY_PRICE_RUB


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_delivery(cart_price_rub: Decimal, total_quantity: int) -> Decimal:
    logger.info(
        "Calculating delivery. cart_price_rub={cart_price_rub}, total_quantity={total_quantity}",
        cart_price_rub=cart_price_rub,
        total_quantity=total_quantity,
    )

    if cart_price_rub >= Decimal("10000"):
        DELIVERY_CALCULATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            result="free",
        ).inc()
        DELIVERY_PRICE_RUB.labels(
            service=SERVICE_NAME,
        ).observe(0.0)
        logger.info(
            "Delivery is free for cart_price_rub={cart_price_rub}",
            cart_price_rub=cart_price_rub,
        )
        return Decimal("0.00")

    base = Decimal("300.00")
    per_item = Decimal("50.00")
    extra_items = max(total_quantity - 1, 0)

    price = _money(base + per_item * extra_items)
    DELIVERY_CALCULATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        result="paid",
    ).inc()
    DELIVERY_PRICE_RUB.labels(
        service=SERVICE_NAME,
    ).observe(float(price))
    logger.info(
        "Delivery calculated. cart_price_rub={cart_price_rub}, total_quantity={total_quantity}, price={price}",
        cart_price_rub=cart_price_rub,
        total_quantity=total_quantity,
        price=price,
    )

    return price
