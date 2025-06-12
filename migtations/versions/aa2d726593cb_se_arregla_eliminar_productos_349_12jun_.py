"""se arregla eliminar productos 349 12jun 2025 Make product_id in images nullable with ondelete CASCADE

Revision ID: aa2d726593cb
Revises: de8a8157d316
Create Date: 2025-06-12 15:54:24.731757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa2d726593cb'
down_revision: Union[str, None] = 'de8a8157d316'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Modificar la columna product_id para que sea nullable
    op.alter_column('images', 'product_id',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_server_default=None)
    # Eliminar la clave foránea existente
    op.drop_constraint('images_ibfk_1', 'images', type_='foreignkey')
    # Añadir una nueva clave foránea con ON DELETE CASCADE
    op.create_foreign_key('images_ibfk_1', 'images', 'products', ['product_id'], ['id_products'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar la clave foránea con ON DELETE CASCADE
    op.drop_constraint('images_ibfk_1', 'images', type_='foreignkey')
    # Restaurar la clave foránea original (sin CASCADE, NOT NULL)
    op.create_foreign_key('images_ibfk_1', 'images', 'products', ['product_id'], ['id_products'])
    # Restaurar la columna product_id a NOT NULL
    op.alter_column('images', 'product_id',
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_server_default=None)