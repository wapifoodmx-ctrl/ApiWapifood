"""Agregar asignacion meseros a mesas

Revision ID: 7f09d4235dd3
Revises: 7e3b21a7d92f
Create Date: 2025-12-10 13:27:15.477474

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '7f09d4235dd3'
down_revision: Union[str, None] = '7e3b21a7d92f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # ### CREAR TABLA DE ASOCIACIÓN (MANY-TO-MANY) ###
    op.create_table('table_waiters',
        # Columna para el ID de la Mesa
        sa.Column('table_id', sa.Integer(), nullable=False),
        
        # Columna para el ID del Mesero
        sa.Column('waiter_id', sa.Integer(), nullable=False),
        
        # Llaves foráneas apuntando a sus respectivas tablas
        sa.ForeignKeyConstraint(['table_id'], ['tables.id_tables'], ),
        sa.ForeignKeyConstraint(['waiter_id'], ['waiters.id'], ),
        
        # OPCIONAL PERO RECOMENDADO: 
        # Hacer que la combinación de ambos sea la llave primaria evita duplicados exactos
        # (que asignes al mismo mesero 2 veces a la misma mesa).
        sa.PrimaryKeyConstraint('table_id', 'waiter_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### BORRAR LA TABLA SI REVERTIMOS ###
    op.drop_table('table_waiters')
    # ### end Alembic commands ###