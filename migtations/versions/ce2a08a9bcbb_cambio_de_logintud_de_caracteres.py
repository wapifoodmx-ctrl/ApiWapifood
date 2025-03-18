"""CAmbio de logintud de caracteres

Revision ID: ce2a08a9bcbb
Revises: 1e8092f3a5b0
Create Date: 2025-03-18 12:14:16.373402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce2a08a9bcbb'
down_revision: Union[str, None] = '1e8092f3a5b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Modificar la columna password para aumentar su longitud
    op.alter_column(
        'users',
        'password',
        existing_type=sa.String(length=50),  # Ajusta esto al tamaño actual de tu columna
        type_=sa.String(length=255),         # Nuevo tamaño
        existing_nullable=False              # Mantén las propiedades actuales
    )

def downgrade():
    # Revertir al tamaño original (ajústalo según tu caso)
    op.alter_column(
        'users',
        'password',
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),          # Tamaño original
        existing_nullable=False
    )