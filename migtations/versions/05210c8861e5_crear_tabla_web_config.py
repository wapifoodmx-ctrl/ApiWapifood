"""Crear tabla web_config

Revision ID: 05210c8861e5
Revises: c1f653497211
Create Date: 2026-02-22 15:57:53.833940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '05210c8861e5'
down_revision: Union[str, None] = 'c1f653497211'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # 1. Crear la tabla web_config de forma aislada y segura
    op.create_table('web_config',
        sa.Column('id_web_config', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('is_delivery_active', sa.Boolean(), server_default=sa.text('1'), nullable=True),
        
        # Llave foránea hacia la tabla de usuarios
        sa.ForeignKeyConstraint(['user_id'], ['users.id_users'], ),
        
        # Llave primaria
        sa.PrimaryKeyConstraint('id_web_config'),
        
        # Aseguramos que solo haya una configuración por restaurante
        sa.UniqueConstraint('user_id')
    )
    
    # 2. Crear índice para el ID
    op.create_index(op.f('ix_web_config_id_web_config'), 'web_config', ['id_web_config'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revertir los cambios en caso de error
    op.drop_index(op.f('ix_web_config_id_web_config'), table_name='web_config')
    op.drop_table('web_config')
