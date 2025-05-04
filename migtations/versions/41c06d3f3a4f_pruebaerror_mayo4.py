"""
Hacer campos opcionales en Restaurante

Revision ID: 41c06d3f3a4f
Revises: <anterior_revision>  # Cambia esto a la revisión anterior válida o None si es la primera
Create Date: <fecha_de_creación>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '41c06d3f3a4f'
down_revision: Union[str, None] = '40d017f9e4d7'  # Ejemplo: '123456789abc' o None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    pass