from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Products as ProductsModel
from app.schemas import Products as ProductsSchema
from app.oauth import get_current_user
from app.db.models import User

 
router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )

# Esquema OAuth2 para el token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.get("/", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def obtenemos_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los productos creados por el usuario autenticado."""
    productos = db.query(ProductsModel).filter(ProductsModel.owner_id == current_user.id_users).all()
    return [ProductsSchema.from_orm(producto) for producto in productos]


@router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
def crear_producto_owner(
    product: ProductsSchema,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea un nuevo producto asignando el owner_id del usuario autenticado."""
    db_product = ProductsModel(
        name=product.name,
        description=product.description,
        price=product.price,
        status=product.status,
        category=product.category,
        owner_id=current_user.id_users
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return ProductsSchema.from_orm(db_product)

@router.put("/{product_id}", response_model=ProductsSchema, status_code=status.HTTP_200_OK)
def actualizar_producto(
    product_id: int,
    product_update: ProductsSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Actualiza un producto existente si pertenece al usuario autenticado."""
    # Buscamos el producto por ID
    db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
    
    # Verificamos si el producto existe
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    # Verificamos si el producto pertenece al usuario autenticado
    if db_product.owner_id != current_user.id_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este producto"
        )
    
    # Actualizamos los campos del producto
    db_product.name = product_update.name
    db_product.description = product_update.description
    db_product.price = product_update.price
    db_product.status = product_update.status
    db_product.category = product_update.category
    
    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(db_product)
    
    return ProductsSchema.from_orm(db_product)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Elimina un producto si pertenece al usuario autenticado."""
    # Buscamos el producto por ID
    db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
    
    # Verificamos si el producto existe
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    # Verificamos si el producto pertenece al usuario autenticado
    if db_product.owner_id != current_user.id_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este producto"
        )
    
    # Eliminamos el producto
    db.delete(db_product)
    db.commit()
    
    return None  # HTTP 204 No Content no devuelve cuerpo