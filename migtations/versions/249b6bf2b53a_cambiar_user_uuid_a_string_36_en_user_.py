"""Cambiar user_uuid a String(36) en user_info 4149jun2025

Revision ID: 249b6bf2b53a
Revises: ef5952e5f27a
Create Date: 2025-06-09 22:15:02.296643

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '249b6bf2b53a'
down_revision: Union[str, None] = 'ef5952e5f27a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cambiar el tipo de la columna user_uuid de Integer a String(36)
    op.alter_column('user_info', 'user_uuid',
                    existing_type=sa.Integer(),
                    type_=sa.String(length=36),
                    existing_nullable=True)

def downgrade() -> None:
    # Revertir el cambio, volviendo a Integer
    op.alter_column('user_info', 'user_uuid',
                    existing_type=sa.String(length=36),
                    type_=sa.Integer(),
                    existing_nullable=True)