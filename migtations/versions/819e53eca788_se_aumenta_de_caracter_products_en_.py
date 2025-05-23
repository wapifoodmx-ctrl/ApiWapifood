"""se aumenta de caracter products en description

Revision ID: 819e53eca788
Revises: 04be2d33b4dd
Create Date: 2025-05-23 12:03:56.744426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '819e53eca788'
down_revision: Union[str, None] = '04be2d33b4dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'products',  # Nombre de la tabla
        'description',  # Nombre de la columna
        existing_type=sa.String(255),  # Tipo actual (ajusta si es diferente)
        type_=sa.String(500),  # Nuevo tipo
        existing_nullable=True  # Si la columna permite valores nulos
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'products',  # Nombre de la tabla
        'description',  # Nombre de la columna
        existing_type=sa.String(500),  # Tipo actual (después del cambio)
        type_=sa.String(255),  # Tipo anterior
        existing_nullable=True  # Si la columna permite valores nulos
    )