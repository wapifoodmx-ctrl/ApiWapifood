"""se añade order un estatus de pedidos 30mayo205

Revision ID: e454ec6595fd
Revises: 55355402608d
Create Date: 2025-05-30 13:23:18.111748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e454ec6595fd'
down_revision: Union[str, None] = '55355402608d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('orders', sa.Column('order_status', sa.Enum('Pendiente', 'EnCocina', 'Preparado', 'Cancelado', 'Completado', name='orderstatusenum'), nullable=False, server_default='Pendiente'))

def downgrade():
    op.drop_column('orders', 'order_status')