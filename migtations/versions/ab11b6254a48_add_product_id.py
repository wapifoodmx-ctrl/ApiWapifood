"""ADD PRODUCT ID

Revision ID: ab11b6254a48
Revises: dfe886c112cd
Create Date: 2025-03-30 16:04:54.453590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab11b6254a48'
down_revision: Union[str, None] = 'dfe886c112cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Verificar si la columna 'product_id' no existe antes de agregarla
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'product_id' not in inspector.get_columns('images'):
        op.add_column('images', sa.Column('product_id', sa.Integer(), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar la columna solo si existe
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'product_id' in inspector.get_columns('images'):
        op.drop_column('images', 'product_id')
