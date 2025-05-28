from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Tables as TablesModel, Payments, TableDetails# Modelo de SQLAlchemy
from app.schemas import Tables as TablesSchema  # Esquema Pydantic
from app.repository.auth import get_current_user
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from app.enums import TablesEnum, SubscriptionAmount # Enum para el estado de las mesas

router = APIRouter(
    prefix="/tables",
    tags=["Tables"]
)
# Esquema para obtener el token del encabezado Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

# @router.post("/tables", response_model=dict, status_code=status.HTTP_201_CREATED)
# def crear_mesa(
#     table: TablesSchema,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)  
# ):
#     """Crea una nueva mesa en la base de datos, asignando el user_id del usuario autenticado."""
#     # Verificar si la mesa ya existe (por número, por ejemplo)
#     existing_table = db.query(TablesModel).filter(TablesModel.number == table.number).first()
#     if existing_table:
#         raise HTTPException(status_code=400, detail="El número de mesa ya existe")
    
#     # Crear nueva mesa
#     try:
#         db_table = TablesModel(
#             number=table.number,
#             capacity=table.capacity,
#             state=table.state,
#             user_id=current_user.id_users  # Asignar el user_id del usuario autenticado
#         )
#         db.add(db_table)
#         db.commit()
#         db.refresh(db_table)
#         return {"mensaje": "Mesa creada exitosamente"}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=400, detail=f"Error creando mesa: {str(e)}")

# @router.get("/tables", response_model=List[TablesSchema], status_code=status.HTTP_200_OK)
# def obtener_las_mesas(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)  
# ):
#     """Obtiene todas las mesas de la base de datos."""
#     # Filtrar las mesas por el usuario autenticado (opcional)
#     mesas = db.query(TablesModel).filter(TablesModel.user_id == current_user.id_users).all()
#     return mesas


#---------------------------------------
#---------------------------------------


# @router.put("/tables/{table_id}", response_model=dict, status_code=status.HTTP_200_OK)
# def actualizamos_mesa(
#     table_id: int,
#     table: TablesSchema,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)  # Corregir aquí
# ):
#     """Actualiza una mesa existente en la base de datos."""
#     db_table = db.query(TablesModel).filter(TablesModel.id_tables == table_id).first()
#     if db_table is None:
#         raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
#     # Verificar si el usuario tiene permiso para actualizar la mesa
#     if db_table.user_id != current_user.id_users:
#         raise HTTPException(status_code=403, detail="No tienes permiso para actualizar esta mesa")

#     # Actualizar los campos
#     try:
#         for key, value in table.dict().items():
#             setattr(db_table, key, value)
#         db.commit()
#         db.refresh(db_table)
#         return {"mensaje": "Mesa actualizada exitosamente"}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=400, detail=f"Error actualizando mesa: {str(e)}")
    

#---------------------------------------
#---------------------------------------

@router.post("/details", status_code=status.HTTP_201_CREATED,
description="Crea los detalles de mesas para un usuario basado en su suscripción."
)
async def create_table_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar la suscripción activa
    payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == "completed"
    ).order_by(Payments.date.desc()).first()

    if not payment or payment.subscription_end_date < datetime.utcnow():
        raise HTTPException(status_code=403, detail="No tienes una suscripción activa")

    # 2. Determinar el número de mesas según el plan
    plan_mesas = {
        "basico": 1,
        "profesional": 16,
        "empresarial": 26
    }
    mesas = plan_mesas.get(payment.plan, 0)
    if mesas == 0:
        raise HTTPException(status_code=400, detail="Plan no reconocido")

    # 3. Verificar si ya existen detalles para este usuario
    existing_details = db.query(TableDetails).filter(TableDetails.user_id == current_user.id_users).all()
    if existing_details:
        raise HTTPException(status_code=400, detail="Los detalles de mesas ya están creados para este usuario")

    # 4. Crear un registro por cada mesa
    table_details = []
    for i in range(1, mesas + 1):
        detail = TableDetails(
            user_id=current_user.id_users,
            table_number=i,
            estado=TablesEnum.Libre,
            cantidad_ventas_por_mesa=0.0
        )
        table_details.append(detail)

    # 5. Guardar todos los detalles en la base de datos
    db.add_all(table_details)
    db.commit()

    return {"message": f"Se han creado {mesas} mesas para el usuario", "mesas": mesas}


#---------------------------------------
#---------------------------------------

@router.post("/generate", status_code=status.HTTP_201_CREATED,
    description="Genera las mesas para un usuario basado en su suscripción activa."
)
async def generate_tables_sub(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar la suscripción activa
    payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == "completed",
        Payments.subscription_end_date >= datetime.utcnow()
    ).order_by(Payments.date.desc()).first()

    if not payment:
        raise HTTPException(status_code=403, detail="No tienes una suscripción activa o válida")

    # 2. Determinar el número de mesas según el monto de la suscripción
    subscription_mesas = {
        100: 1,  # Plan 100 MXN = 1 mesa
        200: 16, # Plan 200 MXN = 16 mesas
        300: 26  # Plan 300 MXN = 26 mesas
    }
    mesas = subscription_mesas.get(payment.amount, 0)
    if mesas == 0:
        raise HTTPException(status_code=400, detail="Monto de suscripción no reconocido")

    # 3. Verificar si ya existen mesas para este usuario
    existing_tables = db.query(TablesModel).filter(TablesModel.user_id == current_user.id_users).all()
    if existing_tables:
        raise HTTPException(status_code=400, detail="Las mesas ya están generadas para este usuario")

    # 4. Crear un registro por cada mesa
    tables = []
    for i in range(1, mesas + 1):
        table = TablesModel(
            number=i,
            capacity=4,  # Valor por defecto de 4 personas (ajustable)
            state=TablesEnum.Libre,
            user_id=current_user.id_users,
            subscription_amount=SubscriptionAmount(payment.amount)  # Asignar el monto de la suscripción
        )
        tables.append(table)

    # 5. Guardar todos los registros en la base de datos
    db.add_all(tables)
    db.commit()

    return {"message": f"Se han generado {mesas} mesas para el usuario", "mesas": mesas}