"""Actualizando plantype de enum para la abse de datos 18_07_2025 4_44pm

Revision ID: 73a9e5e55776
Revises: af09e3200b7b
Create Date: 2025-07-18 16:44:32.056731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '73a9e5e55776'
down_revision: Union[str, None] = 'af09e3200b7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Crear un nuevo ENUM con los valores actualizados
    new_plan_type = sa.Enum(
        'basico', 'profesional', 'empresarial',
        'basico + impresora', 'plan restaurante + impresora', 'plan restaurante plus + impresora',
        name='plantype'
    )
    new_plan_type.create(op.get_bind(), checkfirst=True)

    # Modificar la columna 'plan' para usar el nuevo ENUM
    op.alter_column(
        'payments',
        'plan',
        existing_type=sa.Enum('basico', 'profesional', 'empresarial', name='plantype'),
        type_=new_plan_type,
        nullable=False
    )

def downgrade():
    # Restaurar el ENUM anterior
    old_plan_type = sa.Enum('basico', 'profesional', 'empresarial', name='plantype')
    old_plan_type.create(op.get_bind(), checkfirst=True)

    op.alter_column(
        'payments',
        'plan',
        existing_type=sa.Enum(
            'basico', 'profesional', 'empresarial',
            'basico + impresora', 'plan restaurante + impresora', 'plan restaurante plus + impresora',
            name='plantype'
        ),
        type_=old_plan_type,
        nullable=False
    )

    # Eliminar el ENUM actualizado
    op.execute("DROP TYPE plantype")