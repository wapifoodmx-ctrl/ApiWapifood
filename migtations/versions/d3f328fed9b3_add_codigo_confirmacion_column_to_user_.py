"""Add codigo_confirmacion column to user_info table Vie04jul2025

Revision ID: d3f328fed9b3
Revises: c62ab57bc638
Create Date: 2025-07-04 18:47:54.549767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f328fed9b3'
down_revision: Union[str, None] = 'c62ab57bc638'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column('user_info', sa.Column('codigo_confirmacion', sa.String(length=4), nullable=True))

def downgrade():
    op.drop_column('user_info', 'codigo_confirmacion')