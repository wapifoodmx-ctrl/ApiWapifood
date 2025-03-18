"""add role column admin default

Revision ID: 1e8092f3a5b0
Revises: 0db483539a55
Create Date: 2025-03-18 12:08:35.271469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e8092f3a5b0'
down_revision: Union[str, None] = '0db483539a55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
