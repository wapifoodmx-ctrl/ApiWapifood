"""Cambiamos ticket_number quitando unique 18_07_2025 4_07pm

Revision ID: af09e3200b7b
Revises: 291b3b4dfdda
Create Date: 2025-07-18 16:07:04.776928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'af09e3200b7b'
down_revision: Union[str, None] = '291b3b4dfdda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Eliminar la restricción unique en ticket_number
    op.drop_constraint('ticket_number', 'orders', type_='unique')

def downgrade():
    # Restaurar la restricción unique en ticket_number
    op.create_unique_constraint('ticket_number', 'orders', ['ticket_number'])