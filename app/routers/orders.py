from fastapi import APIRouter, Depends, HTTPException, status, Form
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User
from app.schemas import Orders as OrdersSchema, OrdersResponse, OrdersCreate
from app.db.models import OrdersDetails as OrdersDetailsModel
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


@router.post("/",response_model=OrdersSchema,status_code=status.HTTP_201_CREATED,
    description="Crea una nueva orden y su detalle para un producto existente."
)
async def crear_orden(
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea una nueva orden y su detalle para un producto existente."""
    # 1. Validar la cantidad
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que 0")

    # 2. Verificar que el producto exista y pertenezca al usuario autenticado
    db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")
    if db_product.owner_id != current_user.id_users:
        raise HTTPException(status_code=403, detail="No tienes permiso para crear una orden para este producto")

    # 3. Crear la orden (Orders) asociada al usuario autenticado
    db_order = OrdersModel(
        state="Ocupado",
        date_time=datetime.utcnow(),
        total=db_product.price * quantity,
        orderscol="Orden creada manualmente",
        user_id=current_user.id_users,
        product_name=db_product.name
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 4. Crear el detalle de pedido (OrdersDetails)
    unit_price = db_product.price
    subtotal = quantity * unit_price

    db_order_detail = OrdersDetailsModel(
        order_id=db_order.id_orders,
        product_id=db_product.id_products,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal
    )
    db.add(db_order_detail)
    db.commit()
    db.refresh(db_order_detail)

    return OrdersSchema.from_orm(db_order)

@router.get("/orders", response_model=List[OrdersResponse], status_code=status.HTTP_200_OK)
def obtenemos_orders_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las órdenes del usuario autenticado, incluyendo sus detalles."""
    orders = (
        db.query(OrdersModel)
        .filter(OrdersModel.user_id == current_user.id_users)
        .options(joinedload(OrdersModel.order_details))
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
            "total": order.total,  # Mantener como Decimal
            "orderscol": order.orderscol,
            "user_id": order.user_id,
            "product_name": order.product_name,
            "details": [  # Mapear los detalles manualmente
                {
                    "id_orders_details": detail.id_orders_details,
                    "order_id": detail.order_id,
                    "product_id": detail.product_id,
                    "quantity": detail.quantity,
                    "unit_price": detail.unit_price,  # Mantener como Decimal
                    "subtotal": detail.subtotal  # Mantener como Decimal
                }
                for detail in order.order_details
            ]
        }
        orders_dicts.append(order_dict)

    return [OrdersResponse.model_validate(order_dict) for order_dict in orders_dicts]


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


