"""mercado_pago_preference_id y se eliminan las opciones de stripe 08082025

Revision ID: f55440607777
Revises: 31a7ad355867
Create Date: 2025-08-08 16:11:29.367875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f55440607777'
down_revision: Union[str, None] = '31a7ad355867'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    """"upgrade"""
    # Agregar la nueva columna
    op.add_column('payments', sa.Column('mercado_pago_preference_id', sa.String(length=255), nullable=True))

    
    # Eliminar columnas antiguas
    op.drop_column('payments', 'stripe_payment_intent_id')
    op.drop_column('payments', 'stripe_customer_id')


def downgrade():
    """downgrade"""
    # Restaurar columnas antiguas
    op.add_column('payments', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('payments', sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True))
    
    # Eliminar la columna nueva
    op.drop_column('payments', 'mercado_pago_preference_id')