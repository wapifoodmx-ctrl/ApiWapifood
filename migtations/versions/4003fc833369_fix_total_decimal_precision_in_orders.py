"""Fix total decimal precision in orders

Revision ID: 4003fc833369
Revises: 1347278febdf
Create Date: 2025-11-28 14:48:48.402158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '4003fc833369'
down_revision: Union[str, None] = '1347278febdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### SOLO CAMBIAMOS LA COLUMNA TOTAL ###
    # Cambiamos de DECIMAL(10, 0) a DECIMAL(10, 2) para aceptar centavos (ej: 10.50)
    op.alter_column('orders', 'total',
               existing_type=mysql.DECIMAL(precision=10, scale=0),
               type_=sa.DECIMAL(precision=10, scale=2),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### REVERTIMOS EL CAMBIO ###
    # Volvemos a DECIMAL(10, 0)
    op.alter_column('orders', 'total',
               existing_type=sa.DECIMAL(precision=10, scale=2),
               type_=mysql.DECIMAL(precision=10, scale=0),
               existing_nullable=True)
    # ### end Alembic commands ###