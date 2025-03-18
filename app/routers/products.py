from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Products as ProductsModel  # Modelo de SQLAlchemy
from app.schemas import Products as ProductsSchema  # Esquema Pydantic
from app.repository.auth import get_current_user
from fastapi.security import OAuth2PasswordBearer
from app.db.models import Products


router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )

# Esquema OAuth2 para el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.get("/", response_model=list[ProductsSchema], status_code=status.HTTP_200_OK)
def get_products(db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
 #Aquí pasamos el token como string y lo verificamos con get_current_user
    get_current_user(current_user, db)
    products = db.query(Products).all()
    return products

@router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductsSchema, db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
    # Verifica el token
    get_current_user(current_user, db)
    db_product = Products(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# @router.get("/products", response_model=List[ProductsSchema])
# def obtenemos_productos(db: Session = Depends(get_db)):
#     """Obtiene todos los productos de la base de datos."""
#     productos = db.query(ProductsModel).all()
#     return productos


# @router.post("/products", response_model=dict)
# def creamos_producto(product: ProductsSchema, db: Session = Depends(get_db)):
#     """Crea un nuevo producto en la base de datos."""
#     existing_product = db.query(ProductsModel).filter(ProductsModel.name == product.name).first()
#     if existing_product: #Usamos if para ver si el producto se repite 
#         raise HTTPException(status_code=400, detail="El producto ya existe")
#     db_product = ProductsModel(**product.dict())
#     db.add(db_product)
#     db.commit()
#     db.refresh(db_product)
#     return {"mensaje": "Producto creado exitosamente"}
