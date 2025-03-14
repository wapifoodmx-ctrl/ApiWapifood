from fastapi import APIRouter
from app.schemas import User, UserId
from typing import List
from app.schemas import Orders
from typing import List


usuarios: List[User] = []
orders: List[Orders]= []


 
router = APIRouter(
      prefix="/user",
      tags=["User"],
)


@router.get("/orders", response_model=List[Orders])#Obtenemos las ordenes
def obtener_ordenes():
    return orders

@router.post("/orders", response_model=dict)#Creamos las ordenes
def creamos_ordenes(order: Orders):
    orders.append(order)
    return {"mensaje": "Orden creada exitosamente"}