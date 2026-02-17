"""Agrega order_uuid a web_orders

Revision ID: e7df02201b5c
Revises: 5e057088ba21
Create Date: 2026-02-15 15:26:35.713039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e7df02201b5c'
down_revision: Union[str, None] = '5e057088ba21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """Upgrade schema."""
    # 1. Agregar la columna order_uuid a web_orders
    op.add_column('web_orders', sa.Column('order_uuid', sa.String(length=100), nullable=True))
    
    # 2. Crear el índice para buscar rápido por UUID
    op.create_index(op.f('ix_web_orders_order_uuid'), 'web_orders', ['order_uuid'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revertir los cambios en caso de error
    op.drop_index(op.f('ix_web_orders_order_uuid'), table_name='web_orders')
    op.drop_column('web_orders', 'order_uuid')