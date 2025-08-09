"""se añade checkout_url to payments 07082025

Revision ID: 31a7ad355867
Revises: c9ec79b32393
Create Date: 2025-08-07 21:00:17.276452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31a7ad355867'
down_revision: Union[str, None] = 'c9ec79b32393'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('payments', sa.Column('checkout_url', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('payments', 'checkout_url')