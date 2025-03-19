from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Orders as OrdersModel  # Modelo de SQLAlchemy
from app.schemas import Orders as OrdersSchema  # Esquema Pydantic
from app.repository.auth import get_current_user  # Importar la función de autenticación
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer


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

@router.post("/orders", response_model=dict, status_code=status.HTTP_200_OK)
def creamos_ordenes(order: OrdersSchema, db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
    get_current_user(current_user, db)
    """Crea una nueva orden en la base de datos."""
    # Convertir el esquema Pydantic a un modelo SQLAlchemy
    db_order = OrdersModel(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return {"mensaje": "Orden creada exitosamente"}