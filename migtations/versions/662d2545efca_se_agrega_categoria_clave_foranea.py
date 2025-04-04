"""Se agrega categoria clave foranea

Revision ID: 662d2545efca
Revises: 47b2eea56685
Create Date: 2025-04-04 11:58:28.835710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '662d2545efca'
down_revision: Union[str, None] = '47b2eea56685'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Agregar la columna category_id como nullable inicialmente
    op.add_column('products', sa.Column('category_id', sa.Integer(), nullable=True))

    # 2. Asegurarse de que la tabla categoria tenga al menos una fila
    op.execute("INSERT INTO categoria (nombre_categoria, descripcion_categoria, status) "
               "SELECT 'Sin categoría', 'Categoría predeterminada', 'activo' "
               "WHERE NOT EXISTS (SELECT 1 FROM categoria LIMIT 1)")

    # 3. Asignar un valor predeterminado a category_id (por ejemplo, el ID 1 de categoria)
    op.execute("UPDATE products SET category_id = (SELECT id_categoria FROM categoria LIMIT 1) WHERE category_id IS NULL")

    # 4. Hacer la columna no nullable y agregar la clave foránea
    op.alter_column('products', 'category_id', 
                    existing_type=sa.Integer(),  # Especificar el tipo existente
                    nullable=False)
    op.create_foreign_key(None, 'products', 'categoria', ['category_id'], ['id_categoria'])

def downgrade():
    # Revertir los cambios
    op.drop_constraint(None, 'products', type_='foreignkey')
    op.drop_column('products', 'category_id')