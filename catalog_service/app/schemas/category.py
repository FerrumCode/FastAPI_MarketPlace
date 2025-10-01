import uuid
from datetime import datetime
from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
