# migrations/versions/71632a047aa0_añadiendo_owner_id_a_products.py
"""añadiendo owner_id a products

Revision ID: 71632a047aa0
Revises: b3792d895661
Create Date: <fecha_original>
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '71632a047aa0'
down_revision = 'b3792d895661'
branch_labels = None
depends_on = None

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