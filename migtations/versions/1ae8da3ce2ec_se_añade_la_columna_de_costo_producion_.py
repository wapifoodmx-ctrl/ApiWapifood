"""Se añade la columna de costo_producion  a OrdersDetails 11jul2025 1-08pm

Revision ID: 1ae8da3ce2ec
Revises: e2bfb5362d25
Create Date: 2025-07-11 19:08:42.274774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ae8da3ce2ec'
down_revision: Union[str, None] = 'e2bfb5362d25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    pass
#     # Añadir la columna 'production_cost' a orders_details con valor por defecto 0.00
#     op.add_column('orders_details', 
#                   sa.Column('costo_producion', sa.DECIMAL(10, 2), nullable=False, server_default='0.00'))
def downgrade():
    pass
#     # Eliminar las columnas en orden inverso
#     op.drop_column('orders_details', 'costo_producion')