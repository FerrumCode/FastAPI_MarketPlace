from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class Role(Base):
    __tablename__ = "roles"

    # id SERIAL (PK) # ID роли
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    # name TEXT (UNIQUE) # Название роли (user, manager, admin)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


    users: Mapped[list["User"]] = relationship(back_populates="role")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="roles_permissions",
        back_populates="roles" # Имя атрибута обратной связи в Permission
    )