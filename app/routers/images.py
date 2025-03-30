# app/routers/images.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db  # Asegúrate de tener esta función para obtener la sesión de DB
from app.db.models import Image, User
from app.schemas import ImageCreate, ImageResponse  # Importamos los nuevos esquemas
from fastapi.security import OAuth2PasswordBearer  # Para autenticación
import uuid
from pathlib import Path
from app.oauth import get_current_user
from typing import Optional
from app.db.models import Products  # Asegúrate de importar el modelo de productos

router = APIRouter(
    prefix="/images",
    tags=["images"]
)

# Directorio donde se guardarán las imágenes
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Esquema de autenticación
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/upload/", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
def upload_image(
    file: UploadFile = File(...),
    product_id: Optional[int] = None,  # Hacer product_id opcional como query parameter
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_current_user),  # Obtener el usuario autenticado
    #token: str = Depends(oauth2_scheme)  # Requerir el token
):
    """Sube una imagen y la asocia al usuario autenticado y, opcionalmente, a un producto."""
    # Validar el tipo de archivo (solo imágenes)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    # Verificar que el producto exista si se proporciona un product_id
    if product_id:
        product = db.query(Products).filter(Products.id_products == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Generar un nombre único para el archivo
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Guardar el archivo en el sistema de archivos
    with open(file_path, "wb") as buffer:
        content = file.read()  # No usamos await porque no es necesario en este caso
        buffer.write(content)

    # Crear el registro en la base de datos
    db_image = Image(
        file_name=unique_filename,
        file_path=str(file_path),
        user_id=current_user.id_users,  # Asignar el user_id del usuario autenticado
        product_id=product_id  # Asignar el product_id (puede ser None)
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    # Devolver la respuesta usando el esquema ImageResponse
    return ImageResponse.from_orm(db_image)