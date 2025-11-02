"""Se agrega columna  active a table

Revision ID: 1347278febdf
Revises: deb0fb61046f
Create Date: 2025-10-30 16:38:02.757453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '1347278febdf'
down_revision: Union[str, None] = 'deb0fb61046f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### ÚNICO CAMBIO DESEADO ###
    # Agrega la columna 'is_active' a la tabla 'tables'
    # Nota: server_default='1' (True) es crucial para que no falle en filas existentes
    op.add_column(
        'tables', 
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1'))
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### ÚNICO CAMBIO DESEADO (REVERSA) ###
    op.drop_column('tables', 'is_active')
    # ### end Alembic commands ###