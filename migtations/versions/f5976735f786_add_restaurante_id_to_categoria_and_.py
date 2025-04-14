"""Add restaurante_id to categoria and owner_id to restaurante

Revision ID: f5976735f786
Revises: 7c494168dfbf
Create Date: 2025-04-14 01:10:06.699399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5976735f786'
down_revision: Union[str, None] = '7c494168dfbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Asegurarse de que owner_id exista en restaurante (si no existe, lo crea)
    try:
        op.add_column('restaurante', sa.Column('owner_id', sa.Integer(), nullable=True))
    except Exception as e:
        if "Duplicate column name" in str(e):
            pass  # La columna ya existe, continuamos
        else:
            raise e

    # Asegurarse de que restaurante_id exista en categoria (ya sabemos que existe, pero lo dejamos por completitud)
    try:
        op.add_column('categoria', sa.Column('restaurante_id', sa.Integer(), nullable=True))
    except Exception as e:
        if "Duplicate column name" in str(e):
            pass  # La columna ya existe, continuamos
        else:
            raise e

    # Asegurarse de que restaurante_id sea nullable temporalmente para manejar datos existentes
    op.alter_column('categoria', 'restaurante_id', existing_type=sa.Integer(), nullable=True)

    # Crear un restaurante por defecto si no existe ninguno (asegurándonos de que tenga un owner_id válido)
    # Primero, verificamos si hay un usuario con id_users=1
    op.execute("INSERT INTO users (name, email, password, rol) SELECT 'Admin', 'admin@example.com', 'hashed_password', 'admin' FROM dual WHERE NOT EXISTS (SELECT 1 FROM users WHERE id_users = 1)")
    # Ahora creamos el restaurante con owner_id=1
    op.execute("INSERT INTO restaurante (nombre_restaurante, ciudad, estado_provincia, alcadia, owner_id) SELECT 'Restaurante Por Defecto', 'CDMX', 'Ciudad de México', 'Coyoacán', 1 FROM dual WHERE NOT EXISTS (SELECT 1 FROM restaurante LIMIT 1)")

    # Asignar un valor por defecto a restaurante_id en categoria (usamos el ID del restaurante por defecto)
    op.execute("UPDATE categoria SET restaurante_id = (SELECT id_restaurante FROM restaurante LIMIT 1) WHERE restaurante_id IS NULL")

    # Verificar que no haya registros con restaurante_id nulo
    op.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES';")  # Asegurarse de que MySQL sea estricto
    op.execute("UPDATE categoria SET restaurante_id = (SELECT id_restaurante FROM restaurante LIMIT 1) WHERE restaurante_id IS NULL OR restaurante_id NOT IN (SELECT id_restaurante FROM restaurante)")

    # Asignar un valor por defecto a owner_id en restaurante (usamos el usuario con id_users=1)
    op.execute("UPDATE restaurante SET owner_id = 1 WHERE owner_id IS NULL")

    # Hacer restaurante_id no nullable en categoria
    op.alter_column('categoria', 'restaurante_id', existing_type=sa.Integer(), nullable=False)

    # Hacer owner_id no nullable en restaurante
    op.alter_column('restaurante', 'owner_id', existing_type=sa.Integer(), nullable=False)

    # Añadir las claves foráneas
    op.create_foreign_key('fk_categoria_restaurante_id', 'categoria', 'restaurante', ['restaurante_id'], ['id_restaurante'])
    op.create_foreign_key('fk_restaurante_owner_id', 'restaurante', 'users', ['owner_id'], ['id_users'])

def downgrade():
    # Eliminar las claves foráneas
    op.drop_constraint('fk_categoria_restaurante_id', 'categoria', type_='foreignkey')
    op.drop_constraint('fk_restaurante_owner_id', 'restaurante', type_='foreignkey')

    # Revertir restaurante_id a nullable
    op.alter_column('categoria', 'restaurante_id', existing_type=sa.Integer(), nullable=True)

    # Revertir owner_id a nullable
    op.alter_column('restaurante', 'owner_id', existing_type=sa.Integer(), nullable=True)