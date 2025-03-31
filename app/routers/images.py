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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@router.post("/upload/", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sube una imagen y la asocia al usuario autenticado y, opcionalmente, a un producto."""
    # Validar el tipo de archivo (solo imágenes)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    # Validar la extensión del archivo
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}
    file_extension = f".{file.filename.split('.')[-1].lower()}"
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes con extensiones .jpg, .jpeg, .png o .gif")

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
        content = await file.read()
        buffer.write(content)

    # Crear el registro en la base de datos
    db_image = Image(
        file_name=unique_filename,
        file_path=str(file_path),
        user_id=current_user.id_users,
        product_id=product_id
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return ImageResponse.from_orm(db_image)