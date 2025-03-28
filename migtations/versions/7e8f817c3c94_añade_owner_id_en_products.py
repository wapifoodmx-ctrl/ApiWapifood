"""añade  owner_id en products

Revision ID: 7e8f817c3c94
Revises: 71632a047aa0
Create Date: 2025-03-21 11:48:03.898454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e8f817c3c94'
down_revision: Union[str, None] = '71632a047aa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name, column_name):
    """Verifica si una columna existe en una tabla."""
    connection = op.get_bind()
    result = connection.execute(
        "SELECT COUNT(*) "
        "FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table_name, column_name)
    )
    exists = result.scalar() > 0
    print(f"¿Existe la columna '{column_name}' en la tabla '{table_name}'? {'Sí' if exists else 'No'}")
    return exists

def upgrade():
    # Verificar si la columna owner_id ya existe
    if not _column_exists("products", "owner_id"):
        print("Añadiendo la columna 'owner_id' a la tabla 'products'.")
        op.add_column("products", sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id_users"), nullable=True))
    else:
        print("La columna 'owner_id' ya existe en la tabla 'products'. No se realizará ninguna acción.")

def downgrade():
    # Verificar si la columna owner_id existe antes de eliminarla
    if _column_exists("products", "owner_id"):
        print("Eliminando la columna 'owner_id' de la tabla 'products'.")
        op.drop_column("products", "owner_id")
    else:
        print("La columna 'owner_id' no existe en la tabla 'products'. No se realizará ninguna acción.")