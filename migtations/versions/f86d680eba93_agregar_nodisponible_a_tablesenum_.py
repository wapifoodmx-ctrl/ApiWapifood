"""Agregar NoDisponible a TablesEnum 27jun2025

Revision ID: f86d680eba93
Revises: 32d0b34cd1d8
Create Date: 2025-06-27 20:02:11.771438

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f86d680eba93'
down_revision: Union[str, None] = '32d0b34cd1d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Modificar la columna 'state' en la tabla 'tables' para incluir 'NoDisponible'
    op.alter_column(
        'tables',
        'state',
        existing_type=mysql.ENUM('Libre', 'Ocupado'),
        type_=mysql.ENUM('Libre', 'Ocupado', 'NoDisponible'),
        nullable=False
    )

def downgrade() -> None:
    """Downgrade schema."""
    # Revertir la columna 'state' a su estado original (solo 'Libre' y 'Ocupado')
    op.alter_column(
        'tables',
        'state',
        existing_type=mysql.ENUM('Libre', 'Ocupado', 'NoDisponible'),
        type_=mysql.ENUM('Libre', 'Ocupado'),
        nullable=False
    )