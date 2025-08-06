"""Add Mercado Pago fields to Payments migracion de stripe a mercado pago

Revision ID: c9ec79b32393
Revises: ba9ccad21796
Create Date: 2025-08-06 16:14:04.252501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'c9ec79b32393'
down_revision: Union[str, None] = 'ba9ccad21796'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('payments', sa.Column('mercado_pago_customer_id', sa.String(255), nullable=True))
    op.add_column('payments', sa.Column('mercado_pago_payment_id', sa.String(255), nullable=True))
    op.add_column('payments', sa.Column('mercado_pago_preapproval_id', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('payments', 'mercado_pago_customer_id')
    op.drop_column('payments', 'mercado_pago_payment_id')
    op.drop_column('payments', 'mercado_pago_preapproval_id')