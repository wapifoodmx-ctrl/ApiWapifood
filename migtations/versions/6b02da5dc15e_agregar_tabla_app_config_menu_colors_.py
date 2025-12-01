"""Agregar tabla app_config menu colors 222222222222

Revision ID: 6b02da5dc15e
Revises: 3f650949fa5a
Create Date: 2025-11-28 16:23:11.685160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '6b02da5dc15e'
down_revision: Union[str, None] = '3f650949fa5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. 🧹 LIMPIEZA PREVENTIVA
    # Borramos la tabla vieja 'app_config' si existe para evitar conflictos
    op.execute("DROP TABLE IF EXISTS app_config")
    # Borramos 'Menucolors' si existe para crearla limpia desde cero
    op.execute("DROP TABLE IF EXISTS Menucolors")

    # 2. 🏗️ CREAR TABLA 'Menucolors' COMPLETA
    op.create_table('Menucolors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=1000), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('group', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        
        # 🔐 COLUMNA DE SEGURIDAD
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # LLAVE FORÁNEA
        sa.ForeignKeyConstraint(['user_id'], ['users.id_users'], name='fk_menucolors_user'),
        
        # LLAVE PRIMARIA
        sa.PrimaryKeyConstraint('id')
    )

    # 3. CREAR ÍNDICES Y RESTRICCIONES
    # Índice para buscar rápido por clave
    op.create_index(op.f('ix_Menucolors_key'), 'Menucolors', ['key'], unique=False)
    
    # Restricción única compuesta: Un usuario no puede repetir la misma clave, 
    # pero diferentes usuarios sí pueden tener la misma clave.
    op.create_unique_constraint('uix_user_key', 'Menucolors', ['user_id', 'key'])


def downgrade() -> None:
    # Si revertimos, borramos la tabla nueva
    op.drop_constraint('uix_user_key', 'Menucolors', type_='unique')
    op.drop_index(op.f('ix_Menucolors_key'), table_name='Menucolors')
    op.drop_table('Menucolors')