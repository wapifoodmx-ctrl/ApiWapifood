"""Se quita stock de products

Revision ID: 9cadcaa3ef75
Revises: 10dfe314069c
Create Date: 2025-03-25 12:33:03.983496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cadcaa3ef75'
down_revision: Union[str, None] = '10dfe314069c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
