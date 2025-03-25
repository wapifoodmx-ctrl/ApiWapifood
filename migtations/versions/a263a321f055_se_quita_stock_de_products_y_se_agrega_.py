"""Se quita stock de products y se agrega status

Revision ID: a263a321f055
Revises: 9cadcaa3ef75
Create Date: 2025-03-25 12:39:16.781367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.db.models import StatusEnum


# revision identifiers, used by Alembic.
revision: str = 'a263a321f055'
down_revision: Union[str, None] = '9cadcaa3ef75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Comentamos o eliminamos esta línea porque la columna 'stock' ya no existe
    # op.drop_column('products', 'stock')
    
    # Agregar la columna 'status' como ENUM
    op.add_column('products', sa.Column('status', sa.Enum(StatusEnum), nullable=False, server_default=StatusEnum.activo.value))
    
    # Modificar la longitud de 'category' de VARCHAR(50) a VARCHAR(200)
    op.alter_column('products', 'category', existing_type=sa.String(length=50), type_=sa.String(length=200), nullable=False)

def downgrade():
    # Revertir los cambios: eliminar 'status'
    op.drop_column('products', 'status')
    
    # Revertir la longitud de 'category' de VARCHAR(200) a VARCHAR(50)
    op.alter_column('products', 'category', existing_type=sa.String(length=200), type_=sa.String(length=50), nullable=False)
    
    # Si 'stock' ya no existe, no intentamos restaurarla
    # op.add_column('products', sa.Column('stock', sa.Integer(), nullable=True))