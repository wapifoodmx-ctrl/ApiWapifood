"""add order_id to payments table

Revision ID: 1b10cff467c0
Revises: 7e1b9d906256
Create Date: 2025-05-20 16:14:58.268657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b10cff467c0'
down_revision: Union[str, None] = '7e1b9d906256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column('payments', sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id_orders'), nullable=True))

def downgrade():
    op.drop_column('payments', 'order_id')