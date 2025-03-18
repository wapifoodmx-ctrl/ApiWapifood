from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Orders as OrdersModel  # Modelo de SQLAlchemy
from app.schemas import Orders as OrdersSchema  # Esquema Pydantic

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

@router.get("/orders", response_model=List[OrdersSchema])
def obtener_ordenes(db: Session = Depends(get_db)):
    """Obtiene todas las órdenes de la base de datos."""
    ordenes = db.query(OrdersModel).all()
    return ordenes

@router.post("/orders", response_model=dict)
def creamos_ordenes(order: OrdersSchema, db: Session = Depends(get_db)):
    """Crea una nueva orden en la base de datos."""
    # Convertir el esquema Pydantic a un modelo SQLAlchemy
    db_order = OrdersModel(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return {"mensaje": "Orden creada exitosamente"}