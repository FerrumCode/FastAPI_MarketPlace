from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ReviewBase(BaseModel):
    product_id: str = Field(..., description="UUID строки товара")
    rating: int = Field(..., ge=1, le=5)
    text: Optional[str] = ""

    @field_validator("product_id")
    @classmethod
    def product_id_not_empty(cls, v: str):
        if not v or not isinstance(v, str):
            raise ValueError("product_id is required")
        return v


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    text: Optional[str] = None


class ReviewOut(BaseModel):
    id: str
    product_id: str
    user_id: str
    rating: int
    text: Optional[str] = ""
    created_at: datetime
    updated_at: datetime
