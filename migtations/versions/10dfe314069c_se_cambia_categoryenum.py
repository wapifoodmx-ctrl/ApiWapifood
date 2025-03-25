"""Se cambia categoryEnum

Revision ID: 10dfe314069c
Revises: 7e8f817c3c94
Create Date: 2025-03-25 11:55:55.622469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10dfe314069c'
down_revision: Union[str, None] = '7e8f817c3c94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# En tu archivo de migración de Alembic
def upgrade():
    op.alter_column('products', 'category', existing_type=sa.Enum('activo', 'inactivo', name='categoryenum'), type_=sa.String(50), nullable=False)

def downgrade():
    op.alter_column('products', 'category', existing_type=sa.String(50), type_=sa.Enum('activo', 'inactivo', name='categoryenum'), nullable=False)