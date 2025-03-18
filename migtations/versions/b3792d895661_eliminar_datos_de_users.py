"""Eliminar datos de users

Revision ID: b3792d895661
Revises: ce2a08a9bcbb
Create Date: 2025-03-18 12:39:55.399697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3792d895661'
down_revision: Union[str, None] = 'ce2a08a9bcbb'
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