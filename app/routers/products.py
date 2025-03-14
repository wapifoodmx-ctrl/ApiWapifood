
from fastapi import APIRouter
from app.schemas import User, UserId
from typing import List
from fastapi import HTTPException
from app.schemas import Products

products: List[Products] = []

router = APIRouter(
        prefix="/user",
        tags=["User"],
    )


@router.get("/products", response_model=List[Products])#Obtenemos los productos
def obtenemos_productos():
    return products

@router.post("/products", response_model=dict)#Creamos los productos
def creamos_producto(product: Products):
    products.append(product)
    return {"mensaje": "Producto creado exitosamente"}#Mensaje de producto creado exitosamente



