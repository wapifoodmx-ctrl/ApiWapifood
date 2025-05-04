"""Fusionar cabezas bdad66761e8d y 19d431d1dcbd

Revision ID: e68216d19f47
Revises: bdad66761e8d, 19d431d1dcbd
Create Date: 2025-05-04 16:26:42.702302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e68216d19f47'
down_revision: Union[str, None] = ('bdad66761e8d', '19d431d1dcbd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
