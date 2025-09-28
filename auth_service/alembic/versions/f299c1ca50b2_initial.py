"""initial

Revision ID: f299c1ca50b2
Create Date: 2025-09-19 02:04:16.227213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f299c1ca50b2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # --- Таблица roles ---
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # --- Таблица permissions ---
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # --- Связующая таблица roles_permissions ---
    op.create_table(
        "roles_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True),
    )

    # --- Таблица users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- Добавляем базовые роли ---
    op.execute(
        sa.text("""
        INSERT INTO roles (name, description)
        VALUES
            ('admin', 'Администратор'),
            ('user', 'Обычный пользователь')
        """)
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Удаляем таблицы в обратном порядке (FK → PK)
    op.drop_table("users")
    op.drop_table("roles_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
