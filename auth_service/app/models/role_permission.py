from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Вариант 1
class RolePermission(Base):
    __tablename__ = "roles_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), primary_key=True)


# # Вариант 2
# order_items = Table(
#     "roles_permissions",
#     Base.metadata,
#     Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
#     Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
# )