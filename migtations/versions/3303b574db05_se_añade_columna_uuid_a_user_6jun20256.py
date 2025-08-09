"""se añade columna uuid a user 6jun20256

Revision ID: 3303b574db05
Revises: e454ec6595fd
Create Date: 2025-06-06 13:37:58.938749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3303b574db05'
down_revision: Union[str, None] = 'e454ec6595fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    # Añadir la columna uuid como String(36)
    # op.add_column('users', sa.Column('uuid', sa.String(36), nullable=False))
    # # Opcional: Poblar la columna con valores únicos
    # op.execute("UPDATE users SET uuid = UUID()")

def downgrade():
    """Downgrade schema."""
    # Eliminar la columna uuid
    op.drop_column('users', 'uuid')