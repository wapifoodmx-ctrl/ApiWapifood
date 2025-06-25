"""Merge heads

Revision ID: fd37e3451f4e
Revises: 5c7fd7e1895d, aa2d726593cb
Create Date: 2025-06-13 14:34:49.907200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd37e3451f4e'
down_revision: Union[str, None] = ('5c7fd7e1895d', 'aa2d726593cb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
