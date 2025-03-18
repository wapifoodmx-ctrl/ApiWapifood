"""add role column admin default

Revision ID: 0db483539a55
Revises: 04b425aa8213
Create Date: 2025-03-18 12:06:21.158152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0db483539a55'
down_revision: Union[str, None] = '04b425aa8213'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
