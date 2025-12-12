"""Crear historial de meseros por orden

Revision ID: e327d254f49b
Revises: 7f09d4235dd3
Create Date: 2025-12-12 14:20:31.154357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e327d254f49b'
down_revision: Union[str, None] = '7f09d4235dd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # ### SOLO CREAMOS LA TABLA NUEVA ###
    op.create_table('order_waiter_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('waiter_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        
        # Relaciones (Llaves foráneas)
        sa.ForeignKeyConstraint(['order_id'], ['orders.id_orders'], ),
        sa.ForeignKeyConstraint(['waiter_id'], ['waiters.id'], ),
        
        # Llave primaria
        sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### SI REVERTIMOS, SOLO BORRAMOS LA TABLA ###
    op.drop_table('order_waiter_history')
    # ### end Alembic commands ###