"""Agrega la columna post_orders_uuid para web orders

Revision ID: c1f653497211
Revises: 5141b17c647a
Create Date: 2026-02-19 14:14:14.147026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'c1f653497211'
down_revision: Union[str, None] = '5141b17c647a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Agrega la columna y su índice para buscar rápido
    op.add_column('web_orders', sa.Column('pos_order_uuid', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_web_orders_pos_order_uuid'), 'web_orders', ['pos_order_uuid'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_web_orders_pos_order_uuid'), table_name='web_orders')
    op.drop_column('web_orders', 'pos_order_uuid')
