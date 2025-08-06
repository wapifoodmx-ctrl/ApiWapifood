"""Cambiamos ticket_number a int 18_07_2025 2_52pm

Revision ID: 291b3b4dfdda
Revises: e920b790225c
Create Date: 2025-07-18 14:52:37.320870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '291b3b4dfdda'
down_revision: Union[str, None] = 'e920b790225c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('orders', 'ticket_number',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Integer(),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column('orders', 'ticket_number',
               existing_type=sa.Integer(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
