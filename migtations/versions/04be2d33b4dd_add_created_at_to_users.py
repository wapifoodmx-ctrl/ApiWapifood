"""add created_at to users

Revision ID: 04be2d33b4dd
Revises: c6e23a874329
Create Date: 2025-05-21 12:35:04.661452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04be2d33b4dd'
down_revision: Union[str, None] = 'c6e23a874329'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

def downgrade():
    op.drop_column('users', 'created_at')