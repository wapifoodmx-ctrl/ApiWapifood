"""Fusionar ramas de migración

Revision ID: a2a7e075b6e4
Revises: 3613d754de85, 9c43c29fd4eb
Create Date: 2025-06-08 20:55:49.128556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2a7e075b6e4'
down_revision: Union[str, None] = ('3613d754de85', '9c43c29fd4eb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
