import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2),nullable=False)
    cart_price: Mapped[Decimal] = mapped_column(Numeric(10, 2),nullable=False)
    delivery_price: Mapped[Decimal] = mapped_column(Numeric(10, 2),nullable=False)
    status: Mapped[str] = mapped_column(String(50),default="created",nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())

    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )
