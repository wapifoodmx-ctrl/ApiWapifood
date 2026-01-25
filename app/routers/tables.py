from fastapi import APIRouter, Depends, HTTPException, status, Form
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

# --- MAPA CENTRALIZADO DE PLANES A MESAS ---
# Esta debe ser la ÚNICA fuente de verdad para saber cuántas mesas tiene cada plan.
# Usamos el nombre del plan (en minúsculas) tal como se guarda en la BD.
PLAN_TO_TABLES_MAP = {
    "inauguracion": 3,
    "basico": 3,
    "profesional": 16,
    "empresarial": 26,
    "basico_impresora": 3,
    "restaurante_impresora": 16,
    "plus_restaurante_impresora": 26
}

"""
Se agregó una condición payment.subscription_end_date and para asegurarse de que solo se realice la comparación si 
subscription_end_date no es None. Si es None, la condición not payment ya manejará el caso de un pago inexistente o no válido.
Esto evita el TypeError y permite que el endpoint funcione incluso si subscription_end_date no se ha establecido aún.

"""
@router.post("/details", status_code=status.HTTP_201_CREATED,
    description="Crea o actualiza los detalles de mesas para un usuario basado en su suscripción."
)
async def create_table_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar la suscripción activa (lógica existente)
    payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == "completed",
        Payments.subscription_end_date.isnot(None)
    ).order_by(Payments.date.desc()).first()
    
    if not payment or (payment.subscription_end_date and payment.subscription_end_date < datetime.utcnow()):
        raise HTTPException(status_code=403, detail="No tienes una suscripción activa")

    if not payment.plan:
        raise HTTPException(status_code=400, detail="La suscripción activa no tiene un plan asociado.")

    # 2. Determinar el número de mesas requeridas usando el MAPA CENTRAL
    mesas_requeridas = PLAN_TO_TABLES_MAP.get(payment.plan.lower())
    if mesas_requeridas is None:
        raise HTTPException(status_code=400, detail=f"Plan '{payment.plan}' no reconocido en el mapa de mesas.")

    try:
        # 3. MODIFICADO: Lógica de "Actualizar/Insertar" (Upsert)
        
        # Obtenemos TODOS los detalles de mesas que este usuario haya tenido
        todos_los_detalles = db.query(TableDetails).filter(
            TableDetails.user_id == current_user.id_users
        ).order_by(TableDetails.table_number).all()
        
        # Convertimos la lista en un diccionario para fácil acceso
        # {1: <Objeto TableDetail 1>, 2: <Objeto TableDetail 2>, ...}
        mapa_detalles = {d.table_number: d for d in todos_los_detalles}
        
        detalles_a_crear = []
        
        # --- Parte A: Activar o Crear las mesas necesarias ---
        for i in range(1, mesas_requeridas + 1):
            detalle_existente = mapa_detalles.get(i)
            
            if detalle_existente:
                # La mesa ya existe, solo nos aseguramos de que esté activa
                if not detalle_existente.is_active:
                    detalle_existente.is_active = True
            else:
                # La mesa no existe, la creamos
                nuevo_detalle = TableDetails(
                    user_id=current_user.id_users,
                    table_number=i,
                    estado=TablesEnum.Libre,
                    cantidad_ventas_por_mesa=0.0,
                    is_active=True # Nace activa
                )
                detalles_a_crear.append(nuevo_detalle)

        # --- Parte B: Desactivar las mesas sobrantes ---
        for detalle in todos_los_detalles:
            if detalle.table_number > mesas_requeridas:
                if detalle.is_active:
                    detalle.is_active = False # La desactivamos

        # 5. Guardar todos los cambios
        if detalles_a_crear:
            db.add_all(detalles_a_crear)
        
        db.commit()

        return {"message": f"Se han configurado {mesas_requeridas} mesas para el usuario", "mesas": mesas_requeridas}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear detalles de mesas: {str(e)}")

#---------------------------------------
#---------------------------------------
@router.post("/generate", status_code=status.HTTP_201_CREATED,
    description="Genera o actualiza las mesas (modelo principal) para un usuario basado en su suscripción activa."
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
        
    if not payment.plan:
        raise HTTPException(status_code=400, detail="La suscripción activa no tiene un plan asociado.")

    # 2. Determinar el número de mesas usando el MAPA CENTRAL
    mesas_requeridas = PLAN_TO_TABLES_MAP.get(payment.plan.lower())
    if mesas_requeridas is None:
        raise HTTPException(status_code=400, detail=f"Plan '{payment.plan}' no reconocido en el mapa de mesas.")

    try:
        # 3. Lógica de "Actualizar/Insertar" (Upsert)
        todas_las_mesas = db.query(TablesModel).filter(
            TablesModel.user_id == current_user.id_users
        ).order_by(TablesModel.number).all()
        
        mapa_mesas = {m.number: m for m in todas_las_mesas}
        
        mesas_a_crear = []
        
        # --- Parte A: Activar o Crear las mesas necesarias ---
        for i in range(1, mesas_requeridas + 1):
            mesa_existente = mapa_mesas.get(i)
            
            if mesa_existente:
                if not mesa_existente.is_active:
                    mesa_existente.is_active = True
            else:
                nueva_mesa = TablesModel(
                    number=i,
                    capacity=4,  # Capacidad por defecto
                    state=TablesEnum.Libre,
                    user_id=current_user.id_users,
                    subscription_amount=payment.amount, # Puedes mantener esto si lo usas
                    is_active=True # Nace activa
                )
                mesas_a_crear.append(nueva_mesa)

        # --- Parte B: Desactivar las mesas sobrantes ---
        for mesa in todas_las_mesas:
            if mesa.number > mesas_requeridas:
                if mesa.is_active:
                    mesa.is_active = False # La desactivamos

        # 5. Guardar todos los cambios
        if mesas_a_crear:
            db.add_all(mesas_a_crear)
        
        db.commit()

        return {"message": f"Se han (re)generado {mesas_requeridas} mesas para el usuario", "mesas": mesas_requeridas}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al generar mesas: {str(e)}")

#---------------------------------------
#---------------------------------------
@router.get("/status", response_model=dict, status_code=status.HTTP_200_OK)
def get_tables_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Devuelve la cantidad máxima de mesas y su estado para el usuario autenticado."""
    # 1. Obtener la suscripción
    payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == "completed",
        Payments.subscription_end_date >= datetime.utcnow()
    ).order_by(Payments.date.desc()).first()

    if not payment:
        raise HTTPException(status_code=403, detail="No tienes una suscripción activa o válida")

    if not payment.plan:
        raise HTTPException(status_code=400, detail="La suscripción activa no tiene un plan asociado.")

    # 2. Usar el MAPA CENTRAL para max_mesas
    max_mesas = PLAN_TO_TABLES_MAP.get(payment.plan.lower())
    if max_mesas is None:
        raise HTTPException(status_code=400, detail=f"Plan '{payment.plan}' no reconocido en el mapa de mesas.")

    # 3. Obtener el estado de las mesas ACTIVAS
    tables = db.query(TablesModel).filter(
        TablesModel.user_id == current_user.id_users,
        TablesModel.is_active == True  # <-- ¡EL FILTRO CLAVE!
    ).all()
    
    table_status = {table.number: table.state.value for table in tables}

    return {
        "max_mesas": max_mesas,
        "table_status": table_status
    }

#---------------------------------------
#---------------------------------------


@router.post("/status", response_model=dict, status_code=status.HTTP_200_OK)
def update_table_status(
    number: int = Form(..., description="Número de la mesa a actualizar"),
    state: str = Form(..., description="Nuevo estado de la mesa (Libre u Ocupado)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cambia el estado de una mesa específica entre Libre y Ocupado."""
    # Validar que el estado sea un valor válido de TablesEnum
    try:
        state_enum = TablesEnum(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El estado '{state}' no es válido. Los valores permitidos son: {', '.join([e.value for e in TablesEnum])}"
        )

    # Verificar si la mesa existe para el usuario
    table = db.query(TablesModel).filter(
        TablesModel.number == number,
        TablesModel.user_id == current_user.id_users
    ).first()
    if not table:
        raise HTTPException(status_code=404, detail=f"Mesa {number} no encontrada para este usuario")

    # Validación: Mesa 1 siempre debe estar libre
    if number == 1 and state_enum == TablesEnum.Ocupado:
        raise HTTPException(status_code=403, detail="La mesa 1 siempre debe estar libre (punto de venta)")

    # Validación: No permitir cambiar a Ocupado si ya está Ocupado
    if table.state == TablesEnum.Ocupado and state_enum == TablesEnum.Ocupado:
        raise HTTPException(status_code=400, detail=f"La mesa {number} ya está ocupada")

    # Actualizar el estado
    try:
        table.state = state_enum
        db.commit()
        db.refresh(table)
        return {"mensaje": f"Estado de la mesa {number} actualizado a {state_enum.value}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando el estado de la mesa: {str(e)}")

#---------------------------------------
#---------------------------------------


@router.post("/LiberarTodasLasMesas", response_model=dict, status_code=status.HTTP_200_OK,
description="Libera todas las mesas del usuario autenticado, estableciendo su estado a Libre, basado en la suscripción activa. La mesa número 1 siempre permanece Libre.")
async def release_all_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Libera todas las mesas asociadas al usuario autenticado, estableciendo su estado a Libre.
    La mesa número 1 siempre permanece Libre independientemente de la suscripción.
    Retorna un mensaje con el número de mesas liberadas.
    """
    # 1. Verificar la suscripción activa
    payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == "completed",
        Payments.subscription_end_date >= datetime.utcnow()
    ).order_by(Payments.date.desc()).first()

    if not payment:
        raise HTTPException(status_code=403, detail="No tienes una suscripción activa o válida")

    # 2. Determinar el número máximo de mesas según el monto de la suscripción
    subscription_mesas = {
        100: 1,
        200: 16,
        300: 26
    }
    max_mesas = subscription_mesas.get(payment.amount, 0)
    if max_mesas == 0:
        raise HTTPException(status_code=400, detail="Monto de suscripción no reconocido")

    # 3. Obtener todas las mesas del usuario
    tables = db.query(TablesModel).filter(TablesModel.user_id == current_user.id_users).all()
    if not tables:
        raise HTTPException(status_code=404, detail="No se encontraron mesas para este usuario")

    # 4. Liberar todas las mesas (estado a Libre), respetando la mesa número 1
    updated_tables_count = 0
    for table in tables:
        if table.number != 1:  # La mesa 1 siempre debe estar Libre, no la actualizamos si ya lo está
            if table.state != TablesEnum.Libre:
                table.state = TablesEnum.Libre
                updated_tables_count += 1
        else:
            if table.state != TablesEnum.Libre:  # Asegurar que la mesa 1 esté Libre
                table.state = TablesEnum.Libre
                updated_tables_count += 1

    # 5. Guardar los cambios en la base de datos
    if updated_tables_count > 0:
        db.commit()
        return {"message": f"Se han liberado {updated_tables_count} mesas exitosamente", "mesas_liberadas": updated_tables_count}
    else:
        return {"message": "Todas las mesas ya estaban libres", "mesas_liberadas": 0}