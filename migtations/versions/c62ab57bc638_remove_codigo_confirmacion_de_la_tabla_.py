"""Remove codigo_confirmacion de la tabla orders vie04jul2025

Revision ID: c62ab57bc638
Revises: aa1a9122637c
Create Date: 2025-07-04 18:09:57.283158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c62ab57bc638'
down_revision: Union[str, None] = 'aa1a9122637c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_column('orders', 'codigo_confirmacion')

def downgrade():
    op.add_column('orders', sa.Column('codigo_confirmacion', sa.String(length=4), server_default='0001', nullable=False))