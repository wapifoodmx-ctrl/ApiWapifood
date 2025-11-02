"""Se agrega columna  active a tabledetails

Revision ID: deb0fb61046f
Revises: 36c3c4ca528a
Create Date: 2025-10-30 16:25:17.819871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'deb0fb61046f'
down_revision: Union[str, None] = '36c3c4ca528a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### ÚNICO CAMBIO DESEADO (Versión segura) ###
    # Agrega server_default='1' (True) para que no falle en filas existentes
    op.add_column(
        'table_details', 
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1'))
    )

    
    # ### end Alembic commands ###
def downgrade() -> None:
    """Downgrade schema."""
    # ### ÚNICO CAMBIO DESEADO (REVERSA) ###
    op.drop_column('table_details', 'is_active')
    # ### end Alembic commands ###