from typing import Annotated

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import uuidpk, created_ts
from app.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuidpk]
    name: Mapped[Annotated[str, mapped_column(Text, nullable=False)]]
    created_at: Mapped[created_ts]

    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan"
    )
