"""modifica tabla Menucolors

Revision ID: 85db0c29959b
Revises: 6b02da5dc15e
Create Date: 2025-12-01 14:12:49.659051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '85db0c29959b'
down_revision: Union[str, None] = '6b02da5dc15e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Borramos cualquier versión anterior para empezar limpio
    op.execute("DROP TABLE IF EXISTS app_config")
    op.execute("DROP TABLE IF EXISTS Menucolors")

    # 2. Creamos la tabla de 2 columnas
    op.create_table('menucolors',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id_users'], ),
        sa.PrimaryKeyConstraint('user_id') # <--- El usuario es la llave
    )


def downgrade() -> None:
    op.drop_table('menucolors')