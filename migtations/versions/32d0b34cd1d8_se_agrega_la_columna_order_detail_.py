"""Se agrega la columna order_detail_status, para manejar estados con orders 24jun2025 105pm

Revision ID: 32d0b34cd1d8
Revises: fa829baac42f
Create Date: 2025-06-24 19:05:30.449973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32d0b34cd1d8'
down_revision: Union[str, None] = 'fa829baac42f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    """Upgrade schema."""
    # Agregar la columna order_detail_status a la tabla orders_details
    # op.add_column(
    #     'orders_details',
    #     sa.Column(
    #         'order_detail_status',
    #         sa.Enum('Pendiente', 'EnCocina', 'Preparado', 'Cancelado', 'Completado', 'Finalizado', name='orderstatusenum'),
    #         nullable=False,
    #         server_default='Pendiente'
    #     )
    # )

def downgrade():
    """Downgrade schema."""
    # Eliminar la columna order_detail_status
    op.drop_column('orders_details', 'order_detail_status')