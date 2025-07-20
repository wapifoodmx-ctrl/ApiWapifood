"""Anadir ticket_number a la tabla orders 18_07_2025 1_54pm

Revision ID: e920b790225c
Revises: f79800143983
Create Date: 2025-07-18 13:54:22.799369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e920b790225c'
down_revision: Union[str, None] = 'f79800143983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('orders', sa.Column('ticket_number', sa.String(length=50), nullable=True))
    op.create_unique_constraint(None, 'orders', ['ticket_number'])
  
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'ticket_number')
    # ### end Alembic commands ###
