"""Agregar tabla Menucolors menu colors

Revision ID: 3f650949fa5a
Revises: 4003fc833369
Create Date: 2025-11-28 16:17:26.906006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '3f650949fa5a'
down_revision: Union[str, None] = '4003fc833369'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



# def upgrade() -> None:
#     # ⚠️ 1. Limpiamos la tabla para evitar errores al agregar una columna obligatoria (user_id)
#     # Si tienes datos importantes, respáldalos antes. Como es config de UI, asumimos que se puede reiniciar.
#     op.execute("TRUNCATE TABLE Menucolors")

#     # 2. Agregamos la columna user_id a la tabla existente 'Menucolors'
#     op.add_column('Menucolors', sa.Column('user_id', sa.Integer(), nullable=False))

#     # 3. Creamos la llave foránea que une Menucolors con users
#     op.create_foreign_key('fk_Menucolors_user', 'Menucolors', 'users', ['user_id'], ['id_users'])

#     # 4. Eliminamos el índice único anterior (que no dejaba repetir claves entre usuarios)
#     # Nota: Si te da error diciendo que no existe, comenta esta línea.
#     try:
#         op.drop_index('ix_Menucolors_key', table_name='Menucolors')
#     except Exception:
#         pass # Ignoramos si ya no existía

#     # 5. Creamos el índice normal para búsquedas rápidas por key
#     op.create_index(op.f('ix_Menucolors_key'), 'Menucolors', ['key'], unique=False)

#     # 6. Creamos la restricción única compuesta:
#     # Esto permite que dos usuarios tengan la misma 'key', pero no el mismo usuario dos veces.
#     op.create_unique_constraint('uix_user_key', 'Menucolors', ['user_id', 'key'])


# def downgrade() -> None:
#     # Revertir cambios
#     op.drop_constraint('uix_user_key', 'Menucolors', type_='unique')
#     op.drop_constraint('fk_Menucolors_user', 'Menucolors', type_='foreignkey')
#     op.drop_index(op.f('ix_Menucolors_key'), table_name='Menucolors')
#     op.create_index('ix_Menucolors_key', 'Menucolors', ['key'], unique=True)
#     op.drop_column('Menucolors', 'user_id')


def upgrade() -> None:


    pass 


def downgrade() -> None:
    pass