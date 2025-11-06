from decimal import Decimal

def calc_delivery(cart_price_rub: Decimal) -> Decimal:
    # Простая логика: базовая 300 RUB, если корзина < 2000 RUB +150, иначе 0
    base = Decimal("300.00")
    surcharge = Decimal("150.00") if cart_price_rub < Decimal("2000.00") else Decimal("0.00")
    return base + surcharge
