"""Se cambia la longituf de product name en Orders 3.449jun2025

Revision ID: 5c7fd7e1895d
Revises: 3303b574db05
Create Date: 2025-06-09 15:44:17.773578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c7fd7e1895d'
down_revision: Union[str, None] = '3303b574db05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
