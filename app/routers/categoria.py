from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.db.models import Categoria as CategoriaModel, User, Products as ProductsModel, Categoria #Restaurante
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
BASE_URL = os.getenv("BASE_URL", "https://comandapp-api.h-dev.xyz")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


@router.post("/", response_model=CategoriaSchema, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Crea una nueva categoría asociada al usuario autenticado.
    """
    # Verificar si ya existe una categoría con el mismo nombre para el usuario autenticado
    categoria_existente = (
        db.query(CategoriaModel)
        .filter(
            CategoriaModel.nombre_categoria == categoria.nombre_categoria,
            CategoriaModel.owner_id == current_user.id_users  # Filtrar por el usuario autenticado
        )
        .first()
    )
    if categoria_existente:
        raise HTTPException(status_code=400, detail="Ya existe una categoría con ese nombre para este usuario")

    # Crear la nueva categoría asociada al usuario autenticado
    nueva_categoria = CategoriaModel(
        nombre_categoria=categoria.nombre_categoria,
        descripcion_categoria=categoria.descripcion_categoria,
        status=categoria.status or "activo",
        owner_id=current_user.id_users  # Asociar la categoría al usuario autenticado
    )

    try:
        db.add(nueva_categoria)
        db.commit()
        db.refresh(nueva_categoria)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear la categoría: {str(e)}"
        )

    return nueva_categoria

#---------------------------------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------------------------------


@router.get("/", response_model=List[CategoriaSimple], status_code=status.HTTP_200_OK)
def obtener_lista_categorias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene una lista de categorías asociadas al usuario autenticado."""
    # Obtener categorías asociadas al usuario autenticado
    categorias = (
        db.query(CategoriaModel)
        .filter(CategoriaModel.owner_id == current_user.id_users)
        .all()
    )

    if not categorias:
        raise HTTPException(status_code=404, detail="No se encontraron categorías para el usuario autenticado")

    return categorias

#------------------------------------------------------------------------------------------------------

@router.get("/web-menu/{uuid}", response_model=List[CategoryWithProducts], status_code=status.HTTP_200_OK)
def Muestra_el_menu(
    uuid: str,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_current_user),
    #token: str = Depends(oauth2_scheme)
):
    """Obtiene todas las categorías con sus productos para el usuario identificado por uuid (sin autenticación)."""
    # Buscar el usuario por uuid
    user = db.query(User).filter(User.uuid == uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener categorías asociadas al usuario
    categorias = (
        db.query(CategoriaModel)
        .options(joinedload(CategoriaModel.productos).joinedload(ProductsModel.images))
        .filter(CategoriaModel.owner_id == user.id_users)
        .all()
    )

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
                ],
                "nombre_categoria": categoria.nombre_categoria
            }
            for producto in categoria.productos if producto.owner_id == user.id_users
        ]
        if productos:
            resultado.append({
                "nombre_categoria": categoria.nombre_categoria,
                "productos": productos
            })

    return resultado

#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
