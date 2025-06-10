""" whatsapp en user_info dejar la nomenclatura en minusculas 132pm 10jun2025

Revision ID: de8a8157d316
Revises: bc2f98659acd
Create Date: 2025-06-10 19:32:41.283269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de8a8157d316'
down_revision: Union[str, None] = 'bc2f98659acd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    op.alter_column(
        'user_info',
        'WhatsApp',
        new_column_name='whatsapp',
        existing_type=sa.String(length=50)
    )

def downgrade():
    op.alter_column(
        'user_info',
        'whatsapp',
        new_column_name='WhatsApp',
        existing_type=sa.String(length=50)
    )


# def upgrade():
#     op.alter_column('user_info', 'WhatsApp', new_column_name='whatsapp')

# def downgrade():
#     op.alter_column('user_info', 'whatsapp', new_column_name='WhatsApp')