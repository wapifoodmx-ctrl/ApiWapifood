from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Products as ProductsModel  # Modelo de SQLAlchemy
from app.schemas import Products as ProductsSchema  # Esquema Pydantic


router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )


@router.get("/products", response_model=List[ProductsSchema])
def obtenemos_productos(db: Session = Depends(get_db)):
    """Obtiene todos los productos de la base de datos."""
    productos = db.query(ProductsModel).all()
    return productos


@router.post("/products", response_model=dict)
def creamos_producto(product: ProductsSchema, db: Session = Depends(get_db)):
    """Crea un nuevo producto en la base de datos."""
    existing_product = db.query(ProductsModel).filter(ProductsModel.name == product.name).first()
    if existing_product: #Usamos if para ver si el producto se repite 
        raise HTTPException(status_code=400, detail="El producto ya existe")
    db_product = ProductsModel(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return {"mensaje": "Producto creado exitosamente"}
