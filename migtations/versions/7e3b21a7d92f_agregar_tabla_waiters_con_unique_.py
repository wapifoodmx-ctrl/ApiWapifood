"""Agregar tabla waiters con unique constraint

Revision ID: 7e3b21a7d92f
Revises: 85db0c29959b
Create Date: 2025-12-07 14:15:25.243606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '7e3b21a7d92f'
down_revision: Union[str, None] = '85db0c29959b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # ### SOLO CREAMOS LA TABLA WAITERS ###
    op.create_table('waiters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('access_code', sa.String(length=6), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Relación con la tabla users
        sa.ForeignKeyConstraint(['user_id'], ['users.id_users'], ),
        
        # Llave primaria
        sa.PrimaryKeyConstraint('id'),
        
        # Restricción 1: El UUID debe ser único globalmente
        sa.UniqueConstraint('uuid'),
        
        # Restricción 2 (SEGURIDAD): La combinación (Dueño + Código) debe ser única.
        # Esto permite que dos restaurantes diferentes usen el código '123456',
        # pero el mismo restaurante NO puede tener dos meseros con '123456'.
        sa.UniqueConstraint('user_id', 'access_code', name='uix_waiter_code_per_user')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### SI REVERTIMOS, SOLO BORRAMOS LA TABLA WAITERS ###
    op.drop_table('waiters')
    # ### end Alembic commands ###