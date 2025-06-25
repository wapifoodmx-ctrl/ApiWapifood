# app/repository/user.py
from sqlalchemy.orm import Session, joinedload
from app.db import models
from app.schemas import User, UserInfo, UserInfoCreate, UserInfoResponse, UserInfoByUUIDResponse
from fastapi import HTTPException, status
from app.hashing import Hash
from app.db.models import UserInfo, ImageUser, User
from datetime import datetime
from fastapi import File, UploadFile, HTTPException, status,Form, Depends
from app.db.database import get_db
from typing import Optional
from pydantic import ValidationError
import json
import os
import shutil
from app.db.models import  User
import logging



logger = logging.getLogger(__name__)
UPLOAD_DIR = "app/static/uploads"  # Alinear con products.py
os.makedirs(UPLOAD_DIR, exist_ok=True)

def crear_usuario(usuario, db: Session): 
    usuario = usuario.dict()
    try:
        nuevo_usuario = models.User(
            name=usuario["name"],
            email=usuario["email"],
            password=Hash.hash_password(usuario["password"]),
            rol=usuario["rol"]
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
    except Exception as e:
         raise HTTPException(
              status_code=status.HTTP_409_CONFLICT,
              detail=f"Error creando usuario: {e}"
         )
    


#-------------------------------------------
#-------------------------------------------


def obtener_usuario(user_id, db: Session):
    user = db.query(models.User).filter(models.User.id_users == user_id).first()
    if not user: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el usuario con el id {user_id}"
        )
    return user

def eliminar_usuario(user_id, db: Session):
    user = db.query(models.User).filter(models.User.id_users == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return {"mensaje": "Usuario eliminado exitosamente"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Usuario no encontrado"
    )

def obtener_usuarios(db: Session):
    data = db.query(models.User).all()
    return data 

def actualizar_usuarios(user_id, updateUser, db: Session):
    user = db.query(models.User).filter(models.User.id_users == user_id).first()
    if user:
        # Actualizamos solo los campos que se enviaron en la solicitud
        if updateUser.name is not None:
            user.name = updateUser.name
        if updateUser.email is not None:
            user.email = updateUser.email
        if updateUser.password is not None:
            user.password = updateUser.password
        if updateUser.rol is not None:
            user.rol = updateUser.rol
        db.commit()
        db.refresh(user)
        return {"mensaje": "Usuario actualizado exitosamente"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Usuario no encontrado"
    )


#-------------------------------------------
#-------------------------------------------


def obtener_user_con_info(user_id: int, db: Session):
    user = (
        db.query(models.User)
        .options(
            joinedload(models.User.user_info).joinedload(models.UserInfo.image_user)
        )
        .filter(models.User.id_users == user_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el usuario con el id {user_id}"
        )
    return user

# def create_restaurante(db: Session, nombre_restaurante: str, ciudad: str, estado_provincia: str, alcadia: str, owner_id: int):
#     # Verificar si el owner_id existe en la tabla users
#     owner = db.query(User).filter(User.id_users == owner_id).first()
#     if not owner:
#         raise HTTPException(status_code=404, detail="Usuario no encontrado")

#     # Crear el restaurante
#     db_restaurante = Restaurante(
#         nombre_restaurante=nombre_restaurante,
#         ciudad=ciudad,
#         estado_provincia=estado_provincia,
#         alcadia=alcadia,
#         owner_id=owner_id
#     )
#     try:
#         db.add(db_restaurante)
#         db.commit()
#         db.refresh(db_restaurante)
#         return db_restaurante
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=409, detail=f"Error creando restaurante: {str(e)}")


#-------------------------------------------
#-------------------------------------------


def actualizar_o_crear_user_info(
    user_id: int,
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    codigo_postal: Optional[int] = Form(None),
    ciudad: Optional[str] = Form(None),
    alcaldia: Optional[str] = Form(None),
    nombre_restaurante: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    horario: Optional[str] = Form(None),
    image: UploadFile = None,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id_users == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user_info_record = db.query(UserInfo).filter(UserInfo.user_id == user_id).first()

    if user_info_record:
        user_info_record.nombre = user.name
        user_info_record.email = user.email
        user_info_record.telefono = telefono or user_info_record.telefono
        user_info_record.direccion = direccion or user_info_record.direccion
        user_info_record.codigo_postal = codigo_postal or user_info_record.codigo_postal
        user_info_record.ciudad = ciudad or user_info_record.ciudad
        user_info_record.alcaldia = alcaldia or user_info_record.alcaldia
        user_info_record.nombre_restaurante = nombre_restaurante or user_info_record.nombre_restaurante
        user_info_record.whatsapp = whatsapp or user_info_record.whatsapp
        user_info_record.horario = horario or user_info_record.horario
    else:
        user_info_record = UserInfo(
            user_id=user_id,
            user_uuid=user.uuid,
            nombre=user.name,
            email=user.email,
            telefono=telefono,
            direccion=direccion,
            codigo_postal=codigo_postal,
            ciudad=ciudad,
            alcaldia=alcaldia,
            nombre_restaurante=nombre_restaurante,
            whatsapp=whatsapp,
            horario=horario
        )
        db.add(user_info_record)
    
    db.commit()
    db.refresh(user_info_record)

    if image:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        file_path = f"{UPLOAD_DIR}/{image.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(image.file.read())
        logger.debug(f"Imagen guardada en {file_path}, tamaño: {os.path.getsize(file_path)} bytes")
        image_record = db.query(ImageUser).filter(ImageUser.user_info_id == user_info_record.id_user_info).first()
        if image_record:
            image_record.file_name = image.filename
            image_record.file_path = file_path
        else:
            image_record = ImageUser(
                user_info_id=user_info_record.id_user_info,
                file_name=image.filename,
                file_path=file_path,
            )
            db.add(image_record)

    db.commit()
    db.refresh(user_info_record)

    return user_info_record


#-------------------------------------------
#-------------------------------------------


def obtener_info_por_uuid(user_uuid: str, db: Session) -> Optional[UserInfoByUUIDResponse]:
    """
    Obtiene la información de un usuario (telefono, direccion, nombre_restaurante, whatsapp, image)
    a partir de su user_uuid.
    """
    # Buscar el UserInfo asociado al user_uuid
    user_info = db.query(UserInfo).filter(UserInfo.user_uuid == user_uuid).first()
    
    if not user_info:
        return None

    # Buscar la imagen asociada, si existe
    image_user = db.query(ImageUser).filter(ImageUser.user_info_id == user_info.id_user_info).first()
    image_path = image_user.file_path if image_user else None  # Cambiado de image_path a file_path

    # Crear la respuesta usando el esquema UserInfoByUUIDResponse
    return UserInfoByUUIDResponse(
        telefono=user_info.telefono,
        direccion=user_info.direccion,
        nombre_restaurante=user_info.nombre_restaurante,
        whatsapp=user_info.whatsapp,
        image=image_path
    )