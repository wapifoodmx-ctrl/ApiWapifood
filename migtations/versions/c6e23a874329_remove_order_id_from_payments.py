"""remove order_id from payments

Revision ID: c6e23a874329
Revises: 1b10cff467c0
Create Date: 2025-05-20 16:21:29.750755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6e23a874329'
down_revision: Union[str, None] = '1b10cff467c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # La restricción y la columna ya se eliminaron manualmente
    pass

def downgrade():
    # Revertir los cambios si es necesario (opcional)
    op.add_column('payments', sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id_orders'), nullable=True))
    op.create_foreign_key('payments_ibfk_3', 'payments', 'orders', ['order_id'], ['id_orders'])