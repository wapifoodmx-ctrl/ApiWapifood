"""Añadir tabla_confirmaion poara manejar mejor el codigo jueJUL2025

Revision ID: aa1a9122637c
Revises: 389b3ac55f1c
Create Date: 2025-07-03 18:22:57.904740

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa1a9122637c'
down_revision: Union[str, None] = '389b3ac55f1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    # op.create_table(
    #     'user_confirmation_codes',
    #     sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id_users'), primary_key=True),
    #     sa.Column('codigo_confirmacion', sa.String(length=4), nullable=False, server_default='0001')
    # )

def downgrade():
    """Downgrade schema."""
    op.drop_table('user_confirmation_codes')