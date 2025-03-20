"""añadiendo owner_id a  products

Revision ID: 71632a047aa0
Revises: b3792d895661
Create Date: 2025-03-20 14:59:43.398097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71632a047aa0'
down_revision: Union[str, None] = 'b3792d895661'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column("products", sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id_users"), nullable=True))

def downgrade():
    op.drop_column("products", "owner_id")