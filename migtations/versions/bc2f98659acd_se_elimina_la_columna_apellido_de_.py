"""Se elimina la columna apellido de UserInfo y se agrega la columna WhatsApp 1258 10jun2025

Revision ID: bc2f98659acd
Revises: 249b6bf2b53a
Create Date: 2025-06-10 18:59:01.612834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc2f98659acd'
down_revision: Union[str, None] = '249b6bf2b53a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar columna 'apellido' de la tabla 'userinfo'
    op.drop_column('user_info', 'apellido')

    # Agregar columna 'whatsapp' a la tabla 'userinfo'
    op.add_column('user_info', sa.Column('whatsapp', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Revertir: agregar columna 'apellido'
    op.add_column('user_info', sa.Column('apellido', sa.String(length=50), nullable=True))

    # Revertir: eliminar columna 'whatsapp'
    op.drop_column('user_info', 'whatsapp')