"""Se añade en el enum puntodeventa-- en OrderStatusEnum

Revision ID: 799bf923c627
Revises: 5987317cd058
Create Date: 2025-07-02 21:38:43.408739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.enums import OrderStatusEnum


# revision identifiers, used by Alembic.
revision: str = '799bf923c627'
down_revision: Union[str, None] = '5987317cd058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Crear un nuevo tipo de enumeración que incluya PuntoDeVenta
    order_status_enum = sa.Enum(OrderStatusEnum.Pendiente, OrderStatusEnum.EnCocina, OrderStatusEnum.Preparado,
                               OrderStatusEnum.Cancelado, OrderStatusEnum.Completado, OrderStatusEnum.Finalizado,
                               OrderStatusEnum.PuntoDeVenta, name='orderstatusenum')
    order_status_enum.create(op.get_bind(), checkfirst=True)

    # Actualizar la columna order_status para usar el nuevo tipo de enumeración
    op.alter_column('orders', 'order_status',
                    existing_type=sa.Enum('Pendiente', 'EnCocina', 'Preparado', 'Cancelado', 'Completado', 'Finalizado', name='orderstatusenum'),
                    type_=order_status_enum,
                    existing_nullable=False,
                    postgresql_using='order_status::text::orderstatusenum')

def downgrade():
    # Revertir al enum original (sin PuntoDeVenta)
    old_enum = sa.Enum('Pendiente', 'EnCocina', 'Preparado', 'Cancelado', 'Completado', 'Finalizado', name='orderstatusenum')
    old_enum.create(op.get_bind(), checkfirst=True)

    op.alter_column('orders', 'order_status',
                    existing_type=sa.Enum('Pendiente', 'EnCocina', 'Preparado', 'Cancelado', 'Completado', 'Finalizado', 'PuntoDeVenta', name='orderstatusenum'),
                    type_=old_enum,
                    existing_nullable=False,
                    postgresql_using='order_status::text::orderstatusenum')
