from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Products as ProductsModel
from app.schemas import Products as ProductsSchema
from app.oauth import get_current_user
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


# Opción 2: Crear producto sin owner_id (versión corregida)
@router.post("/products", response_model=dict, status_code=status.HTTP_201_CREATED)
def creamos_producto(
    product: ProductsSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Corregido
):
    """Crea un nuevo producto en la base de datos sin asignar propietario."""
    existing_product = db.query(ProductsModel).filter(ProductsModel.name == product.name).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="El producto ya existe")
    db_product = ProductsModel(**product.dict(exclude={"owner_id"}))  # Excluir owner_id si está presente
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return {"mensaje": "Producto creado exitosamente"}

# Opción 3: Crear producto con owner_id (nueva opción)
@router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
def crear_producto_owner(
    product: ProductsSchema,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea un nuevo producto asignando el owner_id del usuario autenticado."""
    existing_product = db.query(ProductsModel).filter(ProductsModel.name == product.name).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="El producto ya existe")
    db_product = ProductsModel(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        category=product.category,
        owner_id=current_user.id_users  # Asignar el id_users del usuario autenticado
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return ProductsSchema.from_orm(db_product)