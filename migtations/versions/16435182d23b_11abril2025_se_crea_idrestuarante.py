"""11ABRIL2025 SE CREA IDRESTUARANTE

Revision ID: 16435182d23b
Revises: 1b37d42247e2
Create Date: 2025-04-11 16:12:35.477702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16435182d23b'
down_revision: Union[str, None] = '1b37d42247e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Añadir restaurante_id a products, no nullable con default 1
    op.add_column('products', sa.Column('restaurante_id', sa.Integer(), nullable=False, server_default='1'))
    op.create_foreign_key('products_ibfk_3', 'products', 'restaurante', ['restaurante_id'], ['id_restaurante'])
    # Añadir restaurante_id a users, nullable
    op.add_column('users', sa.Column('restaurante_id', sa.Integer(), nullable=True))
    op.create_foreign_key('users_ibfk_1', 'users', 'restaurante', ['restaurante_id'], ['id_restaurante'])

def downgrade():
    # Eliminar claves foráneas y columnas con nombres correctos
    op.drop_constraint('users_ibfk_1', 'users', type_='foreignkey')
    op.drop_column('users', 'restaurante_id')
    op.drop_constraint('products_ibfk_3', 'products', type_='foreignkey')
    op.drop_column('products', 'restaurante_id')