"""Agrega folio web a webOrders

Revision ID: 5141b17c647a
Revises: e7df02201b5c
Create Date: 2026-02-15 16:33:09.168008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '5141b17c647a'
down_revision: Union[str, None] = 'e7df02201b5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregamos la columna folio_web
    op.add_column('web_orders', sa.Column('folio_web', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('web_orders', 'folio_web')
