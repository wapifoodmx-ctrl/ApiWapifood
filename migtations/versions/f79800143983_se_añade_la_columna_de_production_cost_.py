"""Se añade la columna de production_cost  a Products 11jul2025 1-43pm

Revision ID: f79800143983
Revises: 1ae8da3ce2ec
Create Date: 2025-07-11 19:44:11.300253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f79800143983'
down_revision: Union[str, None] = '1ae8da3ce2ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    # Añadir la columna 'production_cost' a la tabla 'products'
    # op.add_column('products', 
    #               sa.Column('production_cost', sa.DECIMAL(10, 2), nullable=False, server_default='0.00'))

def downgrade():
    """Downgrade schema."""
    # Eliminar la columna 'production_cost'
    op.drop_column('products', 'production_cost')