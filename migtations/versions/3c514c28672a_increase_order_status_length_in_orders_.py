"""Increase order_status length in orders table longitud 11:18pm 08jun2025

Revision ID: 3c514c28672a
Revises: 01d2dbe00d9e
Create Date: 2025-06-08 23:18:45.685728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c514c28672a'
down_revision: Union[str, None] = '01d2dbe00d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('orders', 'order_status', type_=sa.String(length=30), existing_type=sa.String(length=10))

def downgrade():
    op.alter_column('orders', 'order_status', type_=sa.String(length=10), existing_type=sa.String(length=20))
