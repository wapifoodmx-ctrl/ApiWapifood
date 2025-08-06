"""Merge heads

Revision ID: ba9ccad21796
Revises: 6e147c410c77, fd37e3451f4e
Create Date: 2025-08-06 16:04:27.107821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba9ccad21796'
down_revision: Union[str, None] = ('6e147c410c77', 'fd37e3451f4e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
