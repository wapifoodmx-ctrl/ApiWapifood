"""Agrega tablas para pedidos web

Revision ID: 5e057088ba21
Revises: 0978806cbb12
Create Date: 2026-02-12 14:42:13.944509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '5e057088ba21'
down_revision: Union[str, None] = '0978806cbb12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Crear tabla Web Orders
    op.create_table('web_orders',
        sa.Column('id_web_orders', sa.Integer(), nullable=False),
        sa.Column('uuid_restaurant', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('customer_name', sa.String(length=150), nullable=True),
        sa.Column('customer_phone', sa.String(length=50), nullable=True),
        sa.Column('customer_address', sa.Text(), nullable=True),
        sa.Column('customer_notes', sa.Text(), nullable=True),
        sa.Column('total', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id_users'], ),
        sa.PrimaryKeyConstraint('id_web_orders')
    )
    op.create_index(op.f('ix_web_orders_id_web_orders'), 'web_orders', ['id_web_orders'], unique=False)

    # 2. Crear tabla Web Order Details
    op.create_table('web_order_details',
        sa.Column('id_web_details', sa.Integer(), nullable=False),
        sa.Column('web_order_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('unit_price', sa.Float(), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=True),
        sa.Column('comment', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id_products'], ),
        sa.ForeignKeyConstraint(['web_order_id'], ['web_orders.id_web_orders'], ),
        sa.PrimaryKeyConstraint('id_web_details')
    )
    op.create_index(op.f('ix_web_order_details_id_web_details'), 'web_order_details', ['id_web_details'], unique=False)


def downgrade() -> None:
    # Borrar tablas en orden inverso
    op.drop_index(op.f('ix_web_order_details_id_web_details'), table_name='web_order_details')
    op.drop_table('web_order_details')
    op.drop_index(op.f('ix_web_orders_id_web_orders'), table_name='web_orders')
    op.drop_table('web_orders')