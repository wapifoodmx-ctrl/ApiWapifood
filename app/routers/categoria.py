from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.db.models import Categoria as CategoriaModel, User, Products as ProductsModel
from app.schemas import Categoria as CategoriaSchema, CategoriaCreate, CategoryWithProducts, CategoriaSimple
from app.oauth import get_current_user
from app.routers.products import BASE_URL
from dotenv import load_dotenv
from typing import List
import os 

router = APIRouter(
    prefix="/categoria",
    tags=["Categoria"],
)

# Cargar variables de entorno
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://192.168.1.69:8000")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.post("/", response_model=CategoriaSchema, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    # Verificar si ya existe una categoría con el mismo nombre
    categoria_existente = db.query(CategoriaModel).filter(CategoriaModel.nombre_categoria == categoria.nombre_categoria).first()
    if categoria_existente:
        raise HTTPException(status_code=400, detail="Ya existe una categoría con ese nombre")

    # Crear la nueva categoría
    nueva_categoria = CategoriaModel(
        nombre_categoria=categoria.nombre_categoria,
        descripcion_categoria=categoria.descripcion_categoria,
        status=categoria.status or "activo"  # Usar "activo" si no se proporciona status
    )
    
    # Agregar a la base de datos
    db.add(nueva_categoria)
    db.commit()
    db.refresh(nueva_categoria)  # Actualiza el objeto con los datos generados (como el ID)

    return nueva_categoria

@router.get("/productos", response_model=List[CategoryWithProducts], status_code=status.HTTP_200_OK)
def obtener_categorias_con_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Obtiene todas las categorías con sus productos creados por el usuario autenticado."""
    # Obtener todas las categorías y cargar las relaciones productos e imágenes
    categorias = (
        db.query(CategoriaModel)
        .options(joinedload(CategoriaModel.productos).joinedload(ProductsModel.images))  # Cargar productos e imágenes
        .all()
    )

    # Construir la respuesta con categorías y sus productos
    resultado = []
    for categoria in categorias:
        productos = [
            {
                "id_products": producto.id_products,
                "name": producto.name,
                "description": producto.description,
                "price": producto.price,
                "category_id": producto.category_id,
                "status": producto.status,
                "image_url": [
                    f"{BASE_URL}/static/uploads/{image.file_name}" for image in producto.images
                ],  # Construir URLs completas
                "nombre_categoria": categoria.nombre_categoria
            }
            for producto in categoria.productos if producto.owner_id == current_user.id_users
        ]
        if productos:  # Solo incluir categorías con productos del usuario
            resultado.append({
                "nombre_categoria": categoria.nombre_categoria,
                "productos": productos
            })

    return resultado



@router.get("/", response_model=List[CategoriaSimple], status_code=status.HTTP_200_OK)
def obtener_lista_categorias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    
):
    """Obtiene una lista de todas las categorías con solo id_categoria y nombre_categoria."""
    categorias = db.query(CategoriaModel).all()
    
    if not categorias:
        raise HTTPException(status_code=404, detail="No se encontraron categorías")

    return categorias