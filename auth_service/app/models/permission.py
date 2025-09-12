from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class Permission(Base):
    __tablename__ = "permissions"

    # id SERIAL PK # ID разрешения
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # code TEXT UNIQUE # Уникальный код (product.create)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # description TEXT # Человеческое описание
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # связи
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="roles_permissions",
        back_populates="permissions"
    )