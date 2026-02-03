# app/routers/waiters.py
from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import Waiter, User
from app.schemas import WaiterCreate, WaiterResponse
from app.oauth import get_current_user # Ajusta el import según tu estructura (auth.py o oauth.py)
from app.db.models import Orders as OrdersModel, Tables as TablesModel, OrderWaiterHistory # Importar modelos
from app.schemas import OrderWithWaitersResponse, WaiterUpdate, WaiterLimitResponse
from sqlalchemy.orm import joinedload
from app.db.models import Payments, PaymentStatus
from app.enums import PaymentStatus
from datetime import datetime

router = APIRouter(
    prefix="/waiters",
    tags=["Waiters / Meseros"]
)


# --- CONFIGURACIÓN DE LÍMITES POR PLAN ---
# Define cuántos meseros permite cada plan
PLAN_WAITER_LIMITS = {
    "inauguracion": 2,
    "basico": 2,
    "profesional": 5,
    "empresarial": 10,
    "basico_impresora": 2,
    "restaurante_impresora": 5,
    "plus_restaurante_impresora": 10
}


# Función auxiliar para obtener el nombre limpio del plan
def get_clean_plan_name(plan_obj):
    if not plan_obj:
        return "sin_plan"
    
    # 1. Si es un Enum, tomamos su .value (ej: "empresarial")
    if hasattr(plan_obj, "value"):
        return str(plan_obj.value).lower()
    
    # 2. Si es string, limpiamos "plantype." por si acaso
    return str(plan_obj).lower().replace("plantype.", "")

# 1. CREAR MESERO (POST) - CON VALIDACIÓN DE PLAN CORREGIDA
@router.post("/", response_model=WaiterResponse, status_code=status.HTTP_201_CREATED)
def create_waiter(
    waiter_data: WaiterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # --- A. VALIDAR LÍMITES DEL PLAN ---
    
    active_payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == PaymentStatus.COMPLETED, 
        Payments.subscription_end_date > datetime.utcnow()
    ).order_by(Payments.date.desc()).first()

    max_waiters = 0
    plan_nombre = "Ninguno"

    if active_payment and active_payment.plan:
        # 👇 USAMOS LA FUNCIÓN DE LIMPIEZA
        plan_nombre = get_clean_plan_name(active_payment.plan)
        max_waiters = PLAN_WAITER_LIMITS.get(plan_nombre, 0)
    
    current_waiters_count = db.query(Waiter).filter(Waiter.user_id == current_user.id_users).count()

    if current_waiters_count >= max_waiters:
        raise HTTPException(
            status_code=403, 
            detail=f"Has alcanzado el límite de meseros para tu plan '{plan_nombre}' ({current_waiters_count}/{max_waiters})."
        )

    # --- B. VALIDAR DUPLICADOS ---
    existing_waiter = db.query(Waiter).filter(
        Waiter.user_id == current_user.id_users,
        Waiter.access_code == waiter_data.access_code
    ).first()

    if existing_waiter:
        raise HTTPException(status_code=400, detail=f"Código {waiter_data.access_code} ya en uso.")

    # --- C. CREAR ---
    new_waiter = Waiter(
        name=waiter_data.name,
        access_code=waiter_data.access_code,
        user_id=current_user.id_users
    )
    db.add(new_waiter)
    db.commit()
    db.refresh(new_waiter)
    return new_waiter


# 2. OBTENER MESEROS (GET)
@router.get("/", response_model=List[WaiterResponse])
def get_my_waiters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    waiters = db.query(Waiter).filter(Waiter.user_id == current_user.id_users).all()
    return waiters


# 3. ACTUALIZAR MESERO (PATCH)
@router.patch("/{waiter_uuid}", response_model=WaiterResponse)
def update_waiter(
    waiter_uuid: str,
    waiter_update: WaiterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_waiter = db.query(Waiter).filter(
        Waiter.uuid == waiter_uuid,
        Waiter.user_id == current_user.id_users
    ).first()

    if not db_waiter: raise HTTPException(status_code=404, detail="Mesero no encontrado")

    if waiter_update.name is not None:
        db_waiter.name = waiter_update.name

    if waiter_update.access_code is not None:
        existing_code = db.query(Waiter).filter(
            Waiter.user_id == current_user.id_users,
            Waiter.access_code == waiter_update.access_code
        ).first()

        if existing_code and existing_code.id != db_waiter.id:
            raise HTTPException(status_code=400, detail=f"Código {waiter_update.access_code} en uso.")
        
        db_waiter.access_code = waiter_update.access_code

    db.commit()
    db.refresh(db_waiter)
    return db_waiter


# 4. ELIMINAR MESERO (DELETE)
@router.delete("/{waiter_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_waiter(
    waiter_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_waiter = db.query(Waiter).filter(
        Waiter.uuid == waiter_uuid,
        Waiter.user_id == current_user.id_users
    ).first()

    if not db_waiter: raise HTTPException(status_code=404, detail="Mesero no encontrado")

    db.delete(db_waiter)
    db.commit()
    return None



# Este es el que necesitas llamar desde el Front para que se guarde la relación
# 5. ASIGNAR MESERO A ORDEN (MODIFICADO PARA HISTORIAL)
@router.post("/assign/order", status_code=status.HTTP_200_OK)
def assign_waiter_to_order(
    order_uuid: str = Body(..., embed=True),
    waiter_uuid: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra que un mesero atendió una orden en este momento.
    Crea un registro histórico. Si el mesero entra, sale y vuelve a entrar, se registrará de nuevo.
    """
    # 1. Buscar la Orden
    order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).first()
    
    if not order: raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Buscar el Mesero
    waiter = db.query(Waiter).filter(
        Waiter.uuid == waiter_uuid,
        Waiter.user_id == current_user.id_users
    ).first()
    
    if not waiter: raise HTTPException(status_code=404, detail="Mesero no encontrado")

    # 3. GUARDAR EN HISTORIAL (Log cronológico)
    # Esto permite: M1 -> M2 -> M1
    history_entry = OrderWaiterHistory(
        order_id=order.id_orders,
        waiter_id=waiter.id
        # assigned_at se llena solo con datetime.utcnow
    )
    db.add(history_entry)

    # 4. (Opcional) Actualizar la asignación actual de la MESA 
    # para que en el dashboard en vivo se vea quién está "actualmente".
    if order.table:
        # Si quieres que la mesa refleje el último, o acumule únicos:
        if waiter not in order.table.assigned_waiters:
            order.table.assigned_waiters.append(waiter)

    db.commit()
    return {
        "message": f"Mesero {waiter.name} registrado en la secuencia de la orden {order_uuid}",
        "timestamp": datetime.utcnow()
    }




# 6. HISTORIAL DE ÓRDENES (GET)
@router.get("/orders-history", response_model=List[OrderWithWaitersResponse])
def get_orders_with_waiters_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = db.query(OrdersModel).options(
        joinedload(OrdersModel.waiter_history).joinedload(OrderWaiterHistory.waiter),
        joinedload(OrdersModel.table),
        joinedload(OrdersModel.order_details)
    ).filter(
        OrdersModel.user_id == current_user.id_users
    ).order_by(OrdersModel.date_time.desc()).all()

    results = []
    for order in orders:
        
        # --- LÓGICA DE FILTRADO (B, A) ---
        
        # 1. Obtenemos todo el historial cronológico
        raw_history = sorted(order.waiter_history, key=lambda x: x.assigned_at)
        
        # 2. Usamos un diccionario para quedarnos SOLO con la última vez que apareció cada uno.
        # Clave: UUID del mesero -> Valor: {Objeto Mesero, Hora}
        unique_waiters_map = {}
        
        for h in raw_history:
            if h.waiter:
                # Al insertar con la misma clave (uuid), se SOBRESCRIBE la vez anterior.
                # Si A entró a las 10:00 y luego a las 10:45, aquí quedará guardado 10:45.
                unique_waiters_map[h.waiter.uuid] = {
                    "waiter_obj": h.waiter,
                    "last_seen": h.assigned_at
                }
        
        # 3. Convertimos el diccionario a lista y ordenamos por esa "última vez vista"
        # Resultado esperado para A->B->A: [B, A]
        sorted_unique_waiters = sorted(
            unique_waiters_map.values(), 
            key=lambda x: x["last_seen"]
        )
        
        # 4. Formateamos para el frontend
        waiters_list = []
        for item in sorted_unique_waiters:
            w_obj = item["waiter_obj"]
            waiters_list.append({
                "name": w_obj.name,
                "uuid": w_obj.uuid
            })
        
        # ---------------------------------

        # B. Detalles (Vacíos como pediste)
        details_list = []
        for d in order.order_details:
            details_list.append({})

        order_dict = {
            "order_uuid": order.order_uuid,
            "waiters": waiters_list, 
            "details": details_list
        }
        results.append(order_dict)
        
    return results


# 7. LIMITES (GET) - CORREGIDO
@router.get("/limits", response_model=WaiterLimitResponse)
def get_waiter_limits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    active_payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == PaymentStatus.COMPLETED,
        Payments.subscription_end_date > datetime.utcnow()
    ).order_by(Payments.date.desc()).first()

    max_waiters = 0
    plan_nombre = "Sin Plan Activo"

    if active_payment and active_payment.plan:
        # 👇 USAMOS LA MISMA FUNCIÓN DE LIMPIEZA
        plan_nombre = get_clean_plan_name(active_payment.plan)
        max_waiters = PLAN_WAITER_LIMITS.get(plan_nombre, 0)

    current_waiters_count = db.query(Waiter).filter(
        Waiter.user_id == current_user.id_users
    ).count()

    remaining = max(0, max_waiters - current_waiters_count)

    return {
        "plan_name": plan_nombre,
        "max_waiters": max_waiters,
        "current_waiters": current_waiters_count,
        "remaining_slots": remaining
    }



# # 1. CREAR MESERO (POST)
# @router.post("/", response_model=WaiterResponse, status_code=status.HTTP_201_CREATED)
# def create_waiter(
#     waiter_data: WaiterCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Registra un nuevo mesero. 
#     Valida que el código no exista YA en ESTE comercio (user_id).
#     """
#     # Validar duplicidad SOLO para este usuario
#     existing_waiter = db.query(Waiter).filter(
#         Waiter.user_id == current_user.id_users,
#         Waiter.access_code == waiter_data.access_code
#     ).first()

#     if existing_waiter:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Ya tienes un mesero registrado con el código {waiter_data.access_code}"
#         )

#     # Crear
#     new_waiter = Waiter(
#         name=waiter_data.name,
#         access_code=waiter_data.access_code,
#         user_id=current_user.id_users # Asignamos al dueño logueado
#     )
    
#     db.add(new_waiter)
#     db.commit()
#     db.refresh(new_waiter)
    
#     return new_waiter

# # 2. OBTENER MESEROS (GET)
# @router.get("/", response_model=List[WaiterResponse])
# def get_my_waiters(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Obtiene la lista de meseros asociados al usuario autenticado.
#     """
#     waiters = db.query(Waiter).filter(Waiter.user_id == current_user.id_users).all()
#     return waiters


# # 4. ACTUALIZAR MESERO (PATCH)
# @router.patch("/{waiter_uuid}", response_model=WaiterResponse)
# def update_waiter(
#     waiter_uuid: str,
#     waiter_update: WaiterUpdate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Actualiza el nombre o el código de acceso de un mesero.
#     Verifica que el nuevo código no esté duplicado en tu comercio.
#     """
#     # 1. Buscar el mesero (Validando que pertenezca al usuario)
#     db_waiter = db.query(Waiter).filter(
#         Waiter.uuid == waiter_uuid,
#         Waiter.user_id == current_user.id_users
#     ).first()

#     if not db_waiter:
#         raise HTTPException(status_code=404, detail="Mesero no encontrado")

#     # 2. Actualizar Nombre (si se envió)
#     if waiter_update.name is not None:
#         db_waiter.name = waiter_update.name

#     # 3. Actualizar Código (si se envió)
#     if waiter_update.access_code is not None:
#         # Verificar que el nuevo código no lo tenga OTRO mesero tuyo
#         existing_code = db.query(Waiter).filter(
#             Waiter.user_id == current_user.id_users,
#             Waiter.access_code == waiter_update.access_code
#         ).first()

#         # Si existe alguien con ese código Y no soy yo mismo... error
#         if existing_code and existing_code.id != db_waiter.id:
#             raise HTTPException(
#                 status_code=400, 
#                 detail=f"El código {waiter_update.access_code} ya está en uso por otro de tus meseros."
#             )
        
#         db_waiter.access_code = waiter_update.access_code

#     db.commit()
#     db.refresh(db_waiter)
#     return db_waiter


# # 5. ELIMINAR MESERO (DELETE)
# @router.delete("/{waiter_uuid}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_waiter(
#     waiter_uuid: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Elimina permanentemente a un mesero.
#     """
#     # 1. Buscar el mesero
#     db_waiter = db.query(Waiter).filter(
#         Waiter.uuid == waiter_uuid,
#         Waiter.user_id == current_user.id_users
#     ).first()

#     if not db_waiter:
#         raise HTTPException(status_code=404, detail="Mesero no encontrado")

#     # 2. Eliminar (SQLAlchemy se encarga de limpiar la tabla intermedia table_waiters automáticamente)
#     db.delete(db_waiter)
#     db.commit()
    
#     return None

# @router.get("/orders-history", response_model=List[OrderWithWaitersResponse])
# def get_orders_with_waiters_info(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Obtiene historial de órdenes simplificado (Solo IDs, fechas, mesa y meseros).
#     """
    
#     # 1. Consulta optimizada
#     orders = db.query(OrdersModel).options(
#         joinedload(OrdersModel.table).joinedload(TablesModel.assigned_waiters),
#         joinedload(OrdersModel.order_details)
#     ).filter(
#         OrdersModel.user_id == current_user.id_users
#     ).order_by(OrdersModel.date_time.desc()).all()

#     results = []

#     for order in orders:
#         # A. Obtener meseros
#         waiters_list = []
#         if order.table and order.table.assigned_waiters:
#             for w in order.table.assigned_waiters:
#                 waiters_list.append({
#                     "name": w.name,
#                     "uuid": w.uuid
#                 })
        
#         # B. Formatear detalles 
#         # (Se agregan diccionarios vacíos porque comentaste los campos)
#         details_list = []
#         for d in order.order_details:
#             details_list.append({
#                 # Campos comentados/removidos por solicitud
#             })

#         # C. Construir objeto de respuesta (Solo campos activos)
#         order_dict = {
#             "id_orders": order.id_orders,
#             "mesa_number": order.table.number if order.table else 0,
#             "date_time": order.date_time,
#             "user_id": order.user_id,
#             "order_uuid": order.order_uuid,
#             "product_name": order.product_name,
            
#             "waiters": waiters_list,
#             "details": details_list
#         }
#         results.append(order_dict)

#     return results