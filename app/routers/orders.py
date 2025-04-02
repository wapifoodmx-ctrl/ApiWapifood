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

# @router.get("/", response_model=List[OrdersSchema], status_code=status.HTTP_200_OK)
# def obtener_ordenes(db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
#     get_current_user(current_user, db)
#     """Obtiene todas las órdenes de la base de datos del usuario."""
#     Orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).all()
#     return Orders


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