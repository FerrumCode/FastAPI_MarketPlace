from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class OrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: List[OrderItemIn]
    target_currency: str = Field(default="RUB", min_length=3, max_length=3)


class OrderStatusPatch(BaseModel):
    status: Literal["created", "paid", "shipped", "delivered", "cancelled"]


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    total_price: Decimal
    cart_price: Decimal
    delivery_price: Decimal
    status: str
    created_at: datetime
    items: List[OrderItemOut]
