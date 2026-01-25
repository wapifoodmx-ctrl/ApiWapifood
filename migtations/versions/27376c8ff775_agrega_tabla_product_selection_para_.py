"""Agrega tabla product_selection para lista personalizada

Revision ID: 27376c8ff775
Revises: e327d254f49b
Create Date: 2026-01-20 16:47:19.565702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '27376c8ff775'
down_revision: Union[str, None] = 'e327d254f49b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # ...
    op.create_table('product_selection',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id_products'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id_users'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # ...
def downgrade():
    op.drop_table('product_selection')