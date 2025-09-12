"""remove default from permission.code

Revision ID: 21bc8d00e0de
Revises: 3ab0f43f3c86
Create Date: 2025-08-23 00:21:09.538642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21bc8d00e0de'
down_revision: Union[str, Sequence[str], None] = '3ab0f43f3c86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
