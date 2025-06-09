"""Se añade la columna user_uui en la tabla UserInfo 08Jun2025 v2

Revision ID: acdbf49e1e4a
Revises: 99ee4bbe0b2a
Create Date: 2025-06-08 20:17:07.789460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acdbf49e1e4a'
down_revision: Union[str, None] = '99ee4bbe0b2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ...existing code...

def upgrade() -> None:
    """Upgrade schema."""
    # Agrega la columna user_uuid a la tabla UserInfo
    op.add_column('UserInfo', sa.Column('user_uuid', sa.Integer(), nullable=False, unique=True))
    # Si necesitas el constraint único explícitamente (algunos backends lo requieren)
    # op.create_unique_constraint('uq_userinfo_user_uuid', 'UserInfo', ['user_uuid'])

def downgrade() -> None:
    """Downgrade schema."""
    # Elimina la columna user_uuid de la tabla UserInfo
    op.drop_column('UserInfo', 'user_uuid')
# ...existing code...