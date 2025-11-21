from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class KafkaOrderItem(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class KafkaOrderEvent(BaseModel):
    event: Literal["ORDER_CREATED", "ORDER_UPDATED"]
    order_id: UUID
    user_id: UUID
    target_currency: str = Field(min_length=3, max_length=3)
    currency_base: str = Field(min_length=3, max_length=3)
    items: List[KafkaOrderItem]
    cart_price: Decimal = Field(ge=0)
    delivery_price: Decimal = Field(ge=0)
    total_price: Decimal = Field(ge=0)
    status: str

    model_config = ConfigDict(extra="ignore")



class FinalOrderItemPatch(BaseModel):
    id: UUID | None = None
    product_id: UUID | None = None
    quantity: int | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class FinalOrderPatch(BaseModel):
    cart_price: Decimal | None = Field(default=None, ge=0)
    delivery_price: Decimal | None = Field(default=None, ge=0)
    total_price: Decimal | None = Field(default=None, ge=0)
    status: Literal["created", "paid", "shipped", "delivered", "cancelled"] | None = None
    items: List[FinalOrderItemPatch] | None = None

    model_config = ConfigDict(extra="forbid")



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
