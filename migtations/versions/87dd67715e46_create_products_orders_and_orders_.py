"""Create products, orders, and orders_details tables

Revision ID: 87dd67715e46
Revises: a263a321f055
Create Date: 2025-03-27 17:14:19.566151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '87dd67715e46'
down_revision: Union[str, None] = 'a263a321f055'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
   # Eliminar o comentar esta línea si la columna 'stock' no existe
    # op.drop_column('products', 'stock')
def downgrade() -> None:
    """Downgrade schema."""
