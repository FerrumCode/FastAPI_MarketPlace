from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class OrderItem:
    product_id: UUID
    quantity: int
    unit_price: Decimal


@dataclass
class OrderPricing:
    order_id: UUID
    cart_price: Decimal
    delivery_price: Decimal
    total_price: Decimal
