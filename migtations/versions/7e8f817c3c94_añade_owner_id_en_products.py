"""añade  owner_id en products

Revision ID: 7e8f817c3c94
Revises: 71632a047aa0
Create Date: 2025-03-21 11:48:03.898454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e8f817c3c94'
down_revision: Union[str, None] = '71632a047aa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("products", sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id_users"), nullable=True))

def downgrade():
    op.drop_column("products", "owner_id")