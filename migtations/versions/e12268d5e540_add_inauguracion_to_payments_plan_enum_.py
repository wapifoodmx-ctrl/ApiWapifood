"""Add inauguracion to Payments plan enum JUE21AGOST2025

Revision ID: e12268d5e540
Revises: f55440607777
Create Date: 2025-08-21 13:56:19.051939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e12268d5e540'
down_revision: Union[str, None] = 'f55440607777'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Modificar la columna plan para incluir 'inauguracion'
    op.alter_column(
        'payments',
        'plan',
        existing_type=sa.Enum(
            'basico',
            'profesional',
            'empresarial',
            'basico_impresora',
            'restaurante_impresora',
            'plus_restaurante_impresora',
            name='plantype'
        ),
        type_=sa.Enum(
            'inauguracion',
            'basico',
            'profesional',
            'empresarial',
            'basico_impresora',
            'restaurante_impresora',
            'plus_restaurante_impresora',
            name='plantype'
        ),
        nullable=False
    )

def downgrade():
    # Revertir la columna plan para eliminar 'inauguracion'
    op.alter_column(
        'payments',
        'plan',
        existing_type=sa.Enum(
            'inauguracion',
            'basico',
            'profesional',
            'empresarial',
            'basico_impresora',
            'restaurante_impresora',
            'plus_restaurante_impresora',
            name='plantype'
        ),
        type_=sa.Enum(
            'basico',
            'profesional',
            'empresarial',
            'basico_impresora',
            'restaurante_impresora',
            'plus_restaurante_impresora',
            name='plantype'
        ),
        nullable=False
    )