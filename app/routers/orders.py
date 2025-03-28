from fastapi import APIRouter, Depends, HTTPException, status
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User
from app.schemas import Orders as OrdersSchema, OrdersResponse
from app.repository.auth import get_current_user
from decimal import Decimal
router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

# Esquema OAuth2 para el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.get("/orders", response_model=List[OrdersSchema], status_code=status.HTTP_200_OK)
def obtener_ordenes(db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
    get_current_user(current_user, db)
    """Obtiene todas las órdenes de la base de datos."""
    ordenes = db.query(OrdersModel).all()
    return ordenes
""" 
@router.post("/orders", response_model=OrdersResponse, status_code=status.HTTP_201_CREATED)
def creamos_ordenes(
    order: OrdersSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    Crea una nueva orden en la base de datos, incluyendo los detalles de la orden.
    # Validar que la mesa exista
    db_table = db.query(TablesModel).filter(TablesModel.id_tables == order.mesa_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail=f"Mesa con ID {order.mesa_id} no encontrada")

    # Validar que los productos existan y calcular el total
    total_calculado = Decimal('0.00')
    for detail in order.order_details:
        # Validar que la cantidad sea mayor que 0
        if detail.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"La cantidad del producto {detail.product_id} debe ser mayor que 0")

        # Obtener el producto de la base de datos
        product = db.query(ProductsModel).filter(ProductsModel.id_products == detail.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto con ID {detail.product_id} no encontrado")

        # Obtener el precio del producto (unit_price)
        unit_price = Decimal(str(product.price))
        # Calcular el subtotal del detalle
        subtotal = unit_price * Decimal(str(detail.quantity))
        total_calculado += subtotal

        # Agregar los valores calculados al detalle para la respuesta
        detail.unit_price = unit_price
        detail.subtotal = subtotal

    try:
        # Crear la orden
        db_order = OrdersModel(
            mesa_id=order.mesa_id,
            state=order.state,
            date_time=order.date_time,
            total=total_calculado,  # Usar el total calculado
            orderscol=order.orderscol,
            user_id=current_user.id_users
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        # Crear los detalles de la orden
        for detail in order.order_details:
            db_detail = OrderDetailsModel(
                order_id=db_order.id_orders,
                product_id=detail.product_id,
                quantity=detail.quantity,
                unit_price=detail.unit_price,
                subtotal=detail.subtotal
            )
            db.add(db_detail)
        
        db.commit()
        db.refresh(db_order)  # Refrescar para incluir los detalles en la respuesta
        return OrdersResponse.from_orm(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando orden: {str(e)}")
     """

@router.get("/orders", response_model=List[OrdersResponse], status_code=status.HTTP_200_OK)
def obtenemos_orders_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las órdenes del usuario autenticado, incluyendo sus detalles."""
    try:
        # Obtener todas las órdenes del usuario autenticado
        orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

        # Devolver las órdenes con sus detalles
        return [OrdersResponse.from_orm(order) for order in orders]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo las órdenes: {str(e)}")