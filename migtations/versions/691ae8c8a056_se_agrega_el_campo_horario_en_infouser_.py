"""se agrega el campo horario en infouser, 310 13jun2025

Revision ID: 691ae8c8a056
Revises: aa2d726593cb
Create Date: 2025-06-13 21:10:25.067129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '691ae8c8a056'
down_revision: Union[str, None] = 'aa2d726593cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'user_info',
        sa.Column('horario', sa.String(50), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_info', 'horario')