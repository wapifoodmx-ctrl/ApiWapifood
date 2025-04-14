from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '16435182d23b'
down_revision: Union[str, None] = '1b37d42247e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Verificar si 'restaurante_id' ya existe en 'products'
    columns_products = inspector.get_columns('products')
    if not any(col['name'] == 'restaurante_id' for col in columns_products):
        op.add_column('products', sa.Column('restaurante_id', sa.Integer(), nullable=False, server_default='1'))
        op.create_foreign_key('products_ibfk_3', 'products', 'restaurante', ['restaurante_id'], ['id_restaurante'])
    
    # Verificar si 'restaurante_id' ya existe en 'users'
    columns_users = inspector.get_columns('users')
    if not any(col['name'] == 'restaurante_id' for col in columns_users):
        op.add_column('users', sa.Column('restaurante_id', sa.Integer(), nullable=True))
        op.create_foreign_key('users_ibfk_1', 'users', 'restaurante', ['restaurante_id'], ['id_restaurante'])

def downgrade():
    # Eliminar claves foráneas y columnas (sin cambios, ya que downgrade debe revertir todo)
    op.drop_constraint('users_ibfk_1', 'users', type_='foreignkey')
    op.drop_column('users', 'restaurante_id')
    op.drop_constraint('products_ibfk_3', 'products', type_='foreignkey')
    op.drop_column('products', 'restaurante_id')