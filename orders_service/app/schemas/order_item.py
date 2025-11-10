from __future__ import annotations

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class OrderItemCreate(BaseModel):
    order_id: UUID
    product_id: UUID
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    product_id: UUID
    quantity: int
    unit_price: float


class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
