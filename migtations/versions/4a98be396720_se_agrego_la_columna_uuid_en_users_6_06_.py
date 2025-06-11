"""Se agrego la columna uuid en users- 6/06/25

Revision ID: 4a98be396720
Revises: e454ec6595fd
Create Date: 2025-06-06 18:45:55.561057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '4a98be396720'
down_revision: Union[str, None] = 'e454ec6595fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Añadir la columna uuid como String(36)
    op.add_column('users', sa.Column('uuid', sa.String(36), nullable=False))
    # Opcional: Poblar la columna con valores únicos
    op.execute("UPDATE users SET uuid = UUID()")

def downgrade():
    # Eliminar la columna uuid
    op.drop_column('users', 'uuid')