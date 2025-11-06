from sqlalchemy import Column, String, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    total_price = Column(Numeric(18, 2), nullable=True)
    cart_price = Column(Numeric(18, 2), nullable=False)
    delivery_price = Column(Numeric(18, 2), nullable=True)
    status = Column(String, nullable=False, default="created")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
