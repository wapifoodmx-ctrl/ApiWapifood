"""Cambiar subscription_amount a Integer en la tabla tables para usar stripe y las nuevas 01082025

Revision ID: 6e147c410c77
Revises: 73a9e5e55776
Create Date: 2025-08-01 19:51:23.445729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e147c410c77'
down_revision: Union[str, None] = '73a9e5e55776'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table('tables', schema=None) as batch_op:
        batch_op.alter_column('subscription_amount',
                              existing_type=sa.VARCHAR(),  # Ajusta el tipo existente según tu esquema actual
                              type_=sa.Integer(),
                              existing_nullable=False)

def downgrade() -> None:
    """Downgrade schema."""
    pass
