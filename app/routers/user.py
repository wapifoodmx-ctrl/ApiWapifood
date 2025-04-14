from fastapi import APIRouter, Depends, status, HTTPException, Form, UploadFile, File
from app.schemas import User, UserId, ShowUser, UserInfo, UserWithInfo, Restaurante, RestauranteCreate, UserInfoCreate, UserInfoResponse
from typing import List
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.db.models import UserInfo, ImageUser, User as UserModel
from app.repository import user
from app.oauth import get_current_user
from app.schemas import User as UserSchema
from app.repository import user as user_repo
from pydantic import ValidationError

 # Importa directamente la función

import os 
import json

router = APIRouter(
    prefix="/user",
    tags=["User"],
)


# Crear la carpeta static/uploadsUser si no existe
UPLOAD_DIR = "static/uploadsUser"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


@router.post("/", status_code=status.HTTP_201_CREATED)  # Al crear los usuarios nos muestra un mensaje
def crear_usuario(usuario: User, db: Session = Depends(get_db)):
    user.crear_usuario(usuario, db)
    return {"mensaje": "Usuario creado exitosamente"}
 

@router.get("/", response_model=List[ShowUser], status_code=status.HTTP_200_OK)
def obtener_usuarios(db: Session = Depends(get_db), 
                    current_user: User = Depends(get_current_user)):
    data = user.obtener_usuarios(db)
    return data

# @router.post('/{user_id}', status_code=status.HTTP_200_OK)  # Post para obtener el usuario a partir del id
# def obtener_usuario(user_id: int, db: Session = Depends(get_db)):
#     usuario = user.obtener_usuario(user_id, db)
#     return {"mensaje": "Usuario no encontrado"}


@router.delete('/{user_id}', status_code=status.HTTP_200_OK)
def eliminar_usuario(user_id: int, db: Session = Depends(get_db), 
                     current_user: User = Depends(get_current_user)):  # Agregar autenticación
    res = user.eliminar_usuario(user_id, db)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {"mensaje": "Usuario eliminado exitosamente"}

# Actualizar un usuario
@router.put('/{user_id}', status_code=status.HTTP_200_OK, response_model=ShowUser)
def actualizar_usuario(user_id: int, updateUser: User, db: Session = Depends(get_db), 
                       current_user: User = Depends(get_current_user)):  # Agregar autenticación
    res = user.actualizar_usuarios(user_id, updateUser, db)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return res

@router.patch("/me/info", status_code=status.HTTP_200_OK, response_model=UserInfoResponse)
async def actualizar_o_crear_user_info(
    user_info: str = Form(...),  # Recibir user_info como una cadena JSON
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user)  # Usar el esquema Pydantic para current_user
):
    """
    Añade o actualiza la información del usuario autenticado.
    """
    # Obtener el user_id desde el usuario autenticado
    user_id = current_user.id_users

    # Verificar si el usuario existe (usando el modelo de SQLAlchemy)
    usuario = db.query(UserModel).filter(UserModel.id_users == user_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Llamar al repositorio para crear o actualizar UserInfo
    try:
        nueva_info = user_repo.actualizar_o_crear_user_info(user_id, user_info, image, db)
        return nueva_info
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="El campo user_info debe ser un JSON válido")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Error de validación en user_info: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Error de valor: {str(e)}")
    except HTTPException as e:
        raise e  # Reenviar excepciones específicas del repositorio
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando información del usuario: {str(e)}"
        )

# Nuevo endpoint para obtener UserInfo del usuario autenticado
@router.get("/me/info", response_model=UserWithInfo, status_code=status.HTTP_200_OK)
def obtener_user_con_info(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):  
    """
    Obtiene la información del usuario autenticado junto con su UserInfo.
    """
    usuario_con_info = user.obtener_user_con_info(current_user.id_users, db)
    if not usuario_con_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario_con_info

