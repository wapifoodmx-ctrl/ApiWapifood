"""add order_analytics table

Revision ID: 7e1b9d906256
Revises: b2e40f1bf9dc
Create Date: 2025-05-20 13:18:22.843802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1b9d906256'
down_revision: Union[str, None] = 'b2e40f1bf9dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'order_analytics',
        sa.Column('id_analytics', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(length=10), nullable=False),
        sa.Column('total_orders', sa.Integer(), nullable=False),
        sa.Column('total_revenue', sa.Float(), nullable=False),
        sa.Column('total_products_sold', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id_users'), nullable=False),
        sa.PrimaryKeyConstraint('id_analytics')
    )

def downgrade():
    op.drop_table('order_analytics')