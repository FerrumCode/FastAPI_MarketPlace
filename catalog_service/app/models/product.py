import uuid
from typing import Annotated

from sqlalchemy import Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import uuidpk, created_ts
from app.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuidpk]
    name: Mapped[Annotated[str, mapped_column(Text, nullable=False)]]
    description: Mapped[Annotated[str, mapped_column(Text)]]
    price: Mapped[Annotated[float, mapped_column(Numeric(10, 2), nullable=False)]]
    category_id: Mapped[
        Annotated[uuid.UUID, mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))]
    ]
    created_at: Mapped[created_ts]

    category: Mapped["Category"] = relationship(back_populates="products")
