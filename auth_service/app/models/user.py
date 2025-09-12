from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    # id # UUID (PK) # Уникальный ID
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # email # TEXT (UNIQUE) # Уникальный Email
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    # password_hash # TEXT # Хеш пароля
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # name # TEXT - Имя
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    # role_id # INT FK → roles.id # Роль
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    # created_at # TIMESTAMP # Дата регистрации
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # связи
    role: Mapped["Role"] = relationship(back_populates="users")