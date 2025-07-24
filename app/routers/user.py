from fastapi import APIRouter, Depends, status, HTTPException, Form, UploadFile, File
from app.schemas import User, UserId, ShowUser, UserInfo, UserWithInfo, UserInfoCreate, UserInfoResponse, UserInfoByUUIDResponse
from app.schemas import PasswordResetRequest, PasswordResetConfirm, PasswordResetResponse
from typing import List
from app.schemas import ConfirmationCodeResponse
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.db.models import UserInfo, ImageUser, User as UserModel
from app.repository import user
from app.oauth import get_current_user
from app.schemas import User as UserSchema
from app.repository import user as user_repo
from pydantic import ValidationError
from typing import Optional


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
 

# @router.get("/", response_model=List[ShowUser], status_code=status.HTTP_200_OK)
# def obtener_usuarios(db: Session = Depends(get_db), 
#                     current_user: User = Depends(get_current_user)):
#     data = user.obtener_usuarios(db)
#     return data

@router.post('/{user_id}', status_code=status.HTTP_200_OK)  # Post para obtener el usuario a partir del id
def obtener_usuario(user_id: int, db: Session = Depends(get_db)):
    usuario = user.obtener_usuario(user_id, db)
    return {"mensaje": "Usuario no encontrado"}


@router.delete('/{user_id}', status_code=status.HTTP_200_OK)
def eliminar_usuario(user_id: int, db: Session = Depends(get_db), 
                     current_user: User = Depends(get_current_user)):  # Agregar autenticación
    res = user.eliminar_usuario(user_id, db)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {"mensaje": "Usuario eliminado exitosamente"}

#-------------------------------------------------------------------------
#--------------------------------------------------------------------------

# Actualizar un usuario
@router.put('/{user_id}', status_code=status.HTTP_200_OK, response_model=ShowUser)
def actualizar_usuario(user_id: int, updateUser: User, db: Session = Depends(get_db), 
                       current_user: User = Depends(get_current_user)):  # Agregar autenticación
    res = user.actualizar_usuarios(user_id, updateUser, db)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return res

#-------------------------------------------------------------------------
#--------------------------------------------------------------------------


@router.patch("/me/info", status_code=status.HTTP_200_OK, response_model=UserInfoResponse)
async def actualizar_o_crear_user_info(
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    codigo_postal: Optional[int] = Form(None),
    ciudad: Optional[str] = Form(None),
    alcaldia: Optional[str] = Form(None),
    nombre_restaurante: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    horario: Optional[str] = Form(None),
    image: UploadFile = File(None),
    codigo_confirmacion: Optional[str] = Form(None),  # Nuevo parámetro opcional,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user)
):
    """
    Añade o actualiza la información del usuario autenticado.
    """
    user_id = current_user.id_users

    usuario = db.query(UserModel).filter(UserModel.id_users == user_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    try:
        nueva_info = user_repo.actualizar_o_crear_user_info(
            user_id=user_id,
            telefono=telefono,
            direccion=direccion,
            codigo_postal=codigo_postal,
            ciudad=ciudad,
            alcaldia=alcaldia,
            nombre_restaurante=nombre_restaurante,
            whatsapp=whatsapp,
            horario=horario,
            image=image,
            codigo_confirmacion=codigo_confirmacion,  # Nuevo campo opcional
            db=db
        )
        return nueva_info
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="El campo user_info debe ser un JSON válido")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Error de validación en user_info: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Error de valor: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando información del usuario: {str(e)}"
        )

#------------------------------------------------------------------------
#-------------------------------------------------------------------------

@router.get("/me/info", response_model=UserWithInfo, status_code=status.HTTP_200_OK)
def obtener_user_con_info(
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user)
):
    """
    Obtiene la información del usuario autenticado junto con su UserInfo.
    """
    usuario_con_info = user_repo.obtener_user_con_info(current_user.id_users, db)
    if not usuario_con_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario_con_info


#------------------------------------------------------------------------
#-------------------------------------------------------------------------

@router.get("/info/{user_uuid}", response_model=UserInfoByUUIDResponse, status_code=status.HTTP_200_OK)
def obtener_info_por_uuid(
    user_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene la información de un usuario (telefono, direccion, nombre_restaurante, whatsapp, image)
    a partir de su user_uuid.
    """
    info = user_repo.obtener_info_por_uuid(user_uuid, db)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Información de usuario no encontrada")
    return info


#------------------------------------------------------------------------
#-------------------------------------------------------------------------


@router.get("/me/confirmation-code", response_model=ConfirmationCodeResponse, status_code=status.HTTP_200_OK)
def obtener_codigo_confirmacion_por_id(
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user)
):
    """
    Obtiene el código de confirmación del usuario autenticado.
    """
    codigo = user_repo.obtener_codigo_confirmacion_por_id(current_user.id_users, db)
    if codigo is None and not db.query(User).filter(User.id_users == current_user.id_users).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if codigo is None and not db.query(UserInfo).filter(UserInfo.user_id == current_user.id_users).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Información de usuario no encontrada")
    return ConfirmationCodeResponse(codigo_confirmacion=codigo)


#------------------------------------------------------------------------
#-------------------------------------------------------------------------

# cambio de contraseña 

@router.post("/password-reset/request", status_code=status.HTTP_200_OK, response_model=PasswordResetResponse)
def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Solicita un restablecimiento de contraseña enviando un enlace por correo.
    """
    return user_repo.request_password_reset(request, db)

@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK, response_model=PasswordResetResponse)
def confirm_password_reset(confirm: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Confirma el restablecimiento de contraseña usando el token y la nueva contraseña.
    """
    return user_repo.confirm_password_reset(confirm, db)