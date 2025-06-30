"""Agregar la columna codigo_confirmacion, con string 3, debido a que solo necesitamos 3 digito0s

Revision ID: 5987317cd058
Revises: f86d680eba93
Create Date: 2025-06-30 19:39:50.228773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5987317cd058'
down_revision: Union[str, None] = 'f86d680eba93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Verificar si la columna ya existe
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'codigo_confirmacion' not in columns:
        # Agregar la columna codigo_confirmacion como nullable temporalmente
        op.add_column('orders', sa.Column('codigo_confirmacion', sa.String(length=3), nullable=True))
        
        # Asignar el mismo código de confirmación (por ejemplo, '000') a todas las filas existentes
        conn = op.get_bind()
        conn.execute(
            sa.text("UPDATE orders SET codigo_confirmacion = :default_code WHERE codigo_confirmacion IS NULL"),
            {"default_code": "000"}
        )
        
        # Hacer la columna no nullable, especificando el tipo existente
        op.alter_column('orders', 'codigo_confirmacion', nullable=False, existing_type=sa.String(length=3))

def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar la columna codigo_confirmacion
    op.drop_column('orders', 'codigo_confirmacion')