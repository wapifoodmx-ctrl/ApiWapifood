"""Add checkout_session_id to payments table intento dos

Revision ID: 1e3d59764cfd
Revises: 1a0e231d165a
Create Date: 2025-05-08 16:35:06.033433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e3d59764cfd'
down_revision: Union[str, None] = '1a0e231d165a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
