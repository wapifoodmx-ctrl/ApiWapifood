# app/routers/waiters.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import Waiter, User
from app.schemas import WaiterCreate, WaiterResponse
from app.oauth import get_current_user # Ajusta el import según tu estructura (auth.py o oauth.py)
from app.db.models import Orders as OrdersModel, Tables as TablesModel # Importar modelos
from app.schemas import OrderWithWaitersResponse, WaiterUpdate
from sqlalchemy.orm import joinedload

router = APIRouter(
    prefix="/waiters",
    tags=["Waiters / Meseros"]
)

# 1. CREAR MESERO (POST)
@router.post("/", response_model=WaiterResponse, status_code=status.HTTP_201_CREATED)
def create_waiter(
    waiter_data: WaiterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra un nuevo mesero. 
    Valida que el código no exista YA en ESTE comercio (user_id).
    """
    # Validar duplicidad SOLO para este usuario
    existing_waiter = db.query(Waiter).filter(
        Waiter.user_id == current_user.id_users,
        Waiter.access_code == waiter_data.access_code
    ).first()

    if existing_waiter:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya tienes un mesero registrado con el código {waiter_data.access_code}"
        )

    # Crear
    new_waiter = Waiter(
        name=waiter_data.name,
        access_code=waiter_data.access_code,
        user_id=current_user.id_users # Asignamos al dueño logueado
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
    """
    Obtiene la lista de meseros asociados al usuario autenticado.
    """
    waiters = db.query(Waiter).filter(Waiter.user_id == current_user.id_users).all()
    return waiters


# 4. ACTUALIZAR MESERO (PATCH)
@router.patch("/{waiter_uuid}", response_model=WaiterResponse)
def update_waiter(
    waiter_uuid: str,
    waiter_update: WaiterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza el nombre o el código de acceso de un mesero.
    Verifica que el nuevo código no esté duplicado en tu comercio.
    """
    # 1. Buscar el mesero (Validando que pertenezca al usuario)
    db_waiter = db.query(Waiter).filter(
        Waiter.uuid == waiter_uuid,
        Waiter.user_id == current_user.id_users
    ).first()

    if not db_waiter:
        raise HTTPException(status_code=404, detail="Mesero no encontrado")

    # 2. Actualizar Nombre (si se envió)
    if waiter_update.name is not None:
        db_waiter.name = waiter_update.name

    # 3. Actualizar Código (si se envió)
    if waiter_update.access_code is not None:
        # Verificar que el nuevo código no lo tenga OTRO mesero tuyo
        existing_code = db.query(Waiter).filter(
            Waiter.user_id == current_user.id_users,
            Waiter.access_code == waiter_update.access_code
        ).first()

        # Si existe alguien con ese código Y no soy yo mismo... error
        if existing_code and existing_code.id != db_waiter.id:
            raise HTTPException(
                status_code=400, 
                detail=f"El código {waiter_update.access_code} ya está en uso por otro de tus meseros."
            )
        
        db_waiter.access_code = waiter_update.access_code

    db.commit()
    db.refresh(db_waiter)
    return db_waiter


# 5. ELIMINAR MESERO (DELETE)
@router.delete("/{waiter_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_waiter(
    waiter_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina permanentemente a un mesero.
    """
    # 1. Buscar el mesero
    db_waiter = db.query(Waiter).filter(
        Waiter.uuid == waiter_uuid,
        Waiter.user_id == current_user.id_users
    ).first()

    if not db_waiter:
        raise HTTPException(status_code=404, detail="Mesero no encontrado")

    # 2. Eliminar (SQLAlchemy se encarga de limpiar la tabla intermedia table_waiters automáticamente)
    db.delete(db_waiter)
    db.commit()
    
    return None




@router.get("/orders-history", response_model=List[OrderWithWaitersResponse])
def get_orders_with_waiters_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes del usuario, incluyendo:
    - Detalles de productos.
    - Lista de MESEROS asignados a la mesa de esa orden.
    """
    
    # 1. Consulta optimizada
    orders = db.query(OrdersModel).options(
        # Cargamos la mesa y sus meseros asignados
        joinedload(OrdersModel.table).joinedload(TablesModel.assigned_waiters),
        # Cargamos los detalles de la orden
        joinedload(OrdersModel.order_details)
    ).filter(
        OrdersModel.user_id == current_user.id_users
    ).order_by(OrdersModel.date_time.desc()).all()

    results = []

    for order in orders:
        # A. Obtener meseros desde la mesa asociada a la orden
        waiters_list = []
        # Verificamos que la orden tenga mesa y que la mesa tenga meseros
        if order.table and order.table.assigned_waiters:
            for w in order.table.assigned_waiters:
                waiters_list.append({
                    "name": w.name,
                    "uuid": w.uuid
                })
        
        # B. Formatear detalles (productos)
        details_list = []
        for d in order.order_details:
            details_list.append({
                "quantity": d.quantity,
                "unit_price": float(d.unit_price) if d.unit_price else 0.0,
                "subtotal": float(d.subtotal) if d.subtotal else 0.0,
                "descuento_details": d.descuento_details,
                "order_detail_status": d.order_detail_status
            })

        # C. Construir objeto de respuesta
        order_dict = {
            "id_orders": order.id_orders,
            "mesa_number": order.table.number if order.table else 0, # Obtenemos el número real
            "state": order.state,
            "order_status": order.order_status,
            "date_time": order.date_time,
            "descuento": order.descuento,
            "total": float(order.total) if order.total else 0.0,
            "orderscol": order.orderscol,
            "user_id": order.user_id,
            "order_uuid": order.order_uuid,
            "product_name": order.product_name,
            
            "waiters": waiters_list, # <--- Aquí van los meseros
            "details": details_list
        }
        results.append(order_dict)

    return results