"""Remove unique constraint from order_uuid para ordenes con la misma mesa 116 pm 14jun2025

Revision ID: f5167883193e
Revises: 691ae8c8a056
Create Date: 2025-06-14 13:16:53.619632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5167883193e'
down_revision: Union[str, None] = '691ae8c8a056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Eliminar la restricción única de la columna order_uuid en la tabla orders
    # with op.batch_alter_table('orders', schema=None) as batch_op:
    #     batch_op.drop_index('order_uuid')  # Corrección: Usar el nombre real del índice


def downgrade() -> None:
    """Downgrade schema."""
    # Restaurar la restricción única en la columna order_uuid (reversible)
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index('order_uuid', ['order_uuid'], unique=True)