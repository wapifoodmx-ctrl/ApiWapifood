"""cambiar la logica de codigo de confirmacion en models tabla Orders a server default jueJUL2025

Revision ID: 389b3ac55f1c
Revises: 799bf923c627
Create Date: 2025-07-03 17:52:49.453246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '389b3ac55f1c'
down_revision: Union[str, None] = '799bf923c627'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('orders', 'codigo_confirmacion',
                    existing_type=sa.String(length=3),  # Longitud original
                    type_=sa.String(length=4),          # Nueva longitud
                    nullable=False,
                    server_default='0001')              # Nuevo valor por defecto

def downgrade():
    op.alter_column('orders', 'codigo_confirmacion',
                    existing_type=sa.String(length=4),
                    type_=sa.String(length=3),
                    nullable=False,
                    server_default=None)