from decimal import Decimal, ROUND_HALF_UP


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_delivery(cart_price_rub: Decimal, total_quantity: int) -> Decimal:
    if cart_price_rub >= Decimal("10000"):
        return Decimal("0.00")

    base = Decimal("300.00")
    per_item = Decimal("50.00")
    extra_items = max(total_quantity - 1, 0)

    return _money(base + per_item * extra_items)
