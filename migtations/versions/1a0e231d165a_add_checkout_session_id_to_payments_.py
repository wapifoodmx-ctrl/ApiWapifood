"""Add checkout_session_id to payments table intento dos

Revision ID: 1a0e231d165a
Revises: 6e238f4140b6
Create Date: 2025-05-08 16:31:11.400804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a0e231d165a'
down_revision: Union[str, None] = '6e238f4140b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # No hacer nada si la columna ya existe
    pass

def downgrade():
    # Esto no se ejecutará a menos que deshagas manualmente
    op.drop_column('payments', 'checkout_session_id')