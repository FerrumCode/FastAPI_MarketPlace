import uuid
from datetime import datetime
from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    category_id: uuid.UUID


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category_id: uuid.UUID | None = None


class ProductRead(ProductBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
