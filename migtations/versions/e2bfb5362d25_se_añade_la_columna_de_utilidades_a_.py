"""Se añade la columna de utilidades a OrdersDetails 11jul2025 12-25pm

Revision ID: e2bfb5362d25
Revises: d3f328fed9b3
Create Date: 2025-07-11 18:25:56.884212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2bfb5362d25'
down_revision: Union[str, None] = 'd3f328fed9b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    # Añadir la columna 'utilidades' a la tabla 'orders_details'
    #op.add_column('orders_details', sa.Column('utilidades', sa.DECIMAL(10, 2), nullable=True))

def downgrade():
    """Downgrade schema."""
    # Eliminar la columna 'utilidades' en caso de revertir la migración
    op.drop_column('orders_details', 'utilidades')