from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Products as ProductsModel
from app.schemas import Products as ProductsSchema
from app.repository.auth import get_current_user
from app.db.models import User
from app.schemas import Products

router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )

# Esquema OAuth2 para el token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


@router.get("/products", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def obtenemos_productos(db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
    get_current_user(current_user, db)
    """Obtiene todos los productos de la base de datos."""
    productos = db.query(ProductsModel).all()
    return productos


@router.post("/products", response_model=dict, status_code=status.HTTP_200_OK)
def creamos_producto(product: ProductsSchema, db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
    get_current_user(current_user, db)
    """Crea un nuevo producto en la base de datos."""
    existing_product = db.query(ProductsModel).filter(ProductsModel.name == product.name).first()
    if existing_product: #Usamos if para ver si el producto se repite 
        raise HTTPException(status_code=400, detail="El producto ya existe")
    db_product = ProductsModel(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return {"mensaje": "Producto creado exitosamente"}
