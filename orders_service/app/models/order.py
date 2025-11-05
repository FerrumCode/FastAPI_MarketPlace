import uuid
from datetime import datetime
from decimal import Decimal  # ИЗМЕНЕНО: использовать Decimal для денег
from typing import List

from sqlalchemy import String, Numeric, DateTime  # УДАЛЕНО: ForeignKey не нужен в этой модели
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base  # ИЗМЕНЕНО: раньше импортировал Base из app.db


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    # Деньги лучше хранить как Decimal, Numeric(10,2) мапится в Decimal.
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )  # ИЗМЕНЕНО: тип -> Decimal

    cart_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )  # ИЗМЕНЕНО: тип -> Decimal

    delivery_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )  # ИЗМЕНЕНО: тип -> Decimal

    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # отношение к OrderItem
    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )
