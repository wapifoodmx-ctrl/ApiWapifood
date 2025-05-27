from fastapi import APIRouter, Depends, HTTPException, status, Form
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User
from app.schemas import Orders as OrdersSchema, OrdersResponse, OrdersCreate
from app.db.models import OrdersDetails as OrdersDetailsModel
from app.db.models import Payments as PaymentsModel
from app.repository.auth import get_current_user
from decimal import Decimal
from datetime import datetime

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

# Esquema OAuth2 para el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

# @router.get("/", response_model=List[OrdersSchema], status_code=status.HTTP_200_OK)
# def obtener_ordenes(db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
#     get_current_user(current_user, db)
#     """Obtiene todas las órdenes de la base de datos del usuario."""
#     Orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).all()
#     return Orders

#------------------------------------------
#------------------------------------------



@router.post("/", response_model=OrdersSchema, status_code=status.HTTP_201_CREATED,
    description="Crea una nueva orden con detalles para múltiples productos existentes."
)
async def crear_orden(
    product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
    quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Crea una nueva orden con detalles para múltiples productos existentes.
    Los product_ids y quantities deben ser cadenas separadas por comas.
    """
    # 1. Parsear las listas de product_ids y quantities
    try:
        product_ids_list = [int(pid) for pid in product_ids.split(",")]
        quantities_list = [int(qty) for qty in quantities.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Los product_ids y quantities deben ser listas de números enteros separados por comas")

    # 2. Validar que las listas tengan la misma longitud
    if len(product_ids_list) != len(quantities_list):
        raise HTTPException(status_code=400, detail="El número de product_ids y quantities debe ser igual")
    if not product_ids_list:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un producto")

    # 3. Validar las cantidades
    for qty in quantities_list:
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Todas las cantidades deben ser mayores que 0")

    # 4. Verificar que los productos existan y pertenezcan al usuario autenticado
    products = []
    total_order = 0.0
    product_names = []
    for product_id in product_ids_list:
        db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
        if not db_product:
            raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")
        if db_product.owner_id != current_user.id_users:
            raise HTTPException(status_code=403, detail=f"No tienes permiso para crear una orden para el producto con ID {product_id}")
        products.append(db_product)
        product_names.append(db_product.name)

    # 5. Crear la orden (Orders) asociada al usuario autenticado
    # Calcular el total de la orden y concatenar los nombres de los productos
    for db_product, qty in zip(products, quantities_list):
        total_order += float(db_product.price) * qty

    db_order = OrdersModel(
        state="Ocupado",
        date_time=datetime.utcnow(),
        total=total_order,
        orderscol="Orden creada manualmente",
        user_id=current_user.id_users,
        product_name=", ".join(product_names)  # Concatenar nombres de productos
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 6. Crear los detalles de pedido (OrdersDetails) para cada producto
    for db_product, qty in zip(products, quantities_list):
        unit_price = float(db_product.price)
        subtotal = qty * unit_price

        db_order_detail = OrdersDetailsModel(
            order_id=db_order.id_orders,
            product_id=db_product.id_products,
            quantity=qty,
            unit_price=unit_price,
            subtotal=subtotal
        )
        db.add(db_order_detail)

    # 7. Confirmar todos los detalles en una sola transacción
    db.commit()

    # 8. Refrescar la orden para incluir los detalles en la respuesta
    db.refresh(db_order)

    return OrdersSchema.from_orm(db_order)

#------------------------------------------
#------------------------------------------

@router.get("/orders", response_model=List[OrdersResponse], status_code=status.HTTP_200_OK)
def obtenemos_orders_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las órdenes del usuario autenticado, incluyendo sus detalles."""
    orders = (
        db.query(OrdersModel)
        .filter(OrdersModel.user_id == current_user.id_users)
        .options(joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product))
        .all()
    )
    
    if not orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

    # Convertir los objetos OrdersModel a diccionarios
    orders_dicts = []
    for order in orders:
        order_dict = {
            "id_orders": order.id_orders,
            "state": order.state,
            "date_time": order.date_time,
            "total": order.total or 0.0,  # Valor por defecto si es None
            "orderscol": order.orderscol or "Sin descripción",
            "user_id": order.user_id,
            "product_name": order.product_name or "Sin nombre",  # Valor por defecto
            "details": [
                {
                    "id_orders_details": detail.id_orders_details,
                    "order_id": detail.order_id,
                    "product_id": detail.product_id,
                    "quantity": detail.quantity,
                    "unit_price": detail.unit_price if detail.unit_price is not None else 0.0,  # Valor por defecto
                    "subtotal": detail.subtotal if detail.subtotal is not None else 0.0  # Valor por defecto
                }
                for detail in order.order_details
            ]
        }
        orders_dicts.append(order_dict)

    return [OrdersResponse.model_validate(order_dict) for order_dict in orders_dicts]

#------------------------------------------
#------------------------------------------

@router.get("/summary", response_model=dict, status_code=status.HTTP_200_OK)
def get_order_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene un resumen de las órdenes del usuario autenticado (Total, Pendientes, En Proceso, Completados)."""
    # Total de órdenes
    total_orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).count()

    # Contar órdenes por estado
    pending = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.state == "Pendiente"
    ).count()
    in_process = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.state == "En Proceso"
    ).count()
    completed = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.state == "Completado"
    ).count()

    # Retornar el resumen
    return {
        "Total de Pedidos": total_orders,
        "Pendientes": pending,
        "En Proceso": in_process,
        "Completados": completed
    }


# @router.get("/orders", response_model=List[OrdersResponse], status_code=status.HTTP_200_OK)
# def obtenemos_orders_details(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Obtiene todas las órdenes del usuario autenticado, incluyendo sus detalles."""
#     try:
#         # Obtener todas las órdenes del usuario autenticado
#         orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).all()
        
#         if not orders:
#             raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

#         # Devolver las órdenes con sus detalles
#         return [OrdersResponse.from_orm(order) for order in orders]
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Error obteniendo las órdenes: {str(e)}")


