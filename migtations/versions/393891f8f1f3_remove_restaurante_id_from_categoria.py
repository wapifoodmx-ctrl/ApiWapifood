"""remove_restaurante_id_from_categoria

Revision ID: 393891f8f1f3
Revises: 120dfccbdbdb
Create Date: 2025-05-04 17:03:19.930811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '393891f8f1f3'
down_revision: Union[str, None] = '120dfccbdbdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# En tu archivo de migración (crea uno manualmente)
def upgrade():
    # Elimina todas las FKs primero
    op.drop_constraint('users_ibfk_X', 'users', type_='foreignkey')  # Reemplaza X con el número correcto
    op.drop_constraint('categoria_ibfk_X', 'categoria', type_='foreignkey')
    op.drop_constraint('products_ibfk_X', 'products', type_='foreignkey')
    
    # Luego elimina las columnas
    op.drop_column('users', 'restaurante_id')
    op.drop_column('categoria', 'restaurante_id')
    op.drop_column('products', 'restaurante_id')
    
    # Si existe la tabla restaurante y quieres eliminarla:
    op.drop_table('restaurante')

def downgrade() -> None:
    
    """Downgrade schema."""
