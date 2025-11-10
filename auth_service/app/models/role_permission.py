from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RolePermission(Base):
    __tablename__ = "roles_permissions"

    # role_id # INTEGER # FK → roles.id
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)

    # permission_id # INTEGER # FK → permissions.id
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), primary_key=True)