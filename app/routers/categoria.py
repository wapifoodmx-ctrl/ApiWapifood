from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Categoria as CategoriaModel, User
from app.schemas import Categoria as CategoriaSchema, CategoriaCreate
from app.oauth import get_current_user

router = APIRouter(
    prefix="/categoria",
    tags=["Categoria"],
)

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