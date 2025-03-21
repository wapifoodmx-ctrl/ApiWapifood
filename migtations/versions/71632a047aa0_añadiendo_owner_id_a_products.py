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

def upgrade():
    # Añadir la columna owner_id
    op.add_column("products", sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id_users"), nullable=True))

def downgrade():
    # Eliminar la columna owner_id
    op.drop_column("products", "owner_id")