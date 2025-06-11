# app/repository/user.py
from sqlalchemy.orm import Session, joinedload
from app.db import models
from app.schemas import User, UserInfo, UserInfoCreate
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

UPLOAD_DIR = "static/uploadsUser"

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

# def crear_user_info(user_id: int, user_info_str: str, image: UploadFile | None, db: Session):
#     try:
#         # Parsear el user_info de cadena JSON a un objeto
#         user_info_dict = json.loads(user_info_str)
#         user_info = UserInfoCreate(**user_info_dict)

#         # Verificar si ya existe un UserInfo para este usuario
#         existing_info = db.query(UserInfo).filter(UserInfo.user_id == user_id).first()
#         if existing_info:
#             raise HTTPException(
#                 status_code=409,
#                 detail="Ya existe información personal para este usuario"
#             )

#         # Crear UserInfo
#         nueva_info = UserInfo(
#             nombre=user_info.nombre,
#             apellido=user_info.apellido,
#             email=user_info.email,
#             telefono=user_info.telefono,
#             direccion=user_info.direccion,
#             codigo_postal=user_info.codigo_postal,
#             ciudad=user_info.ciudad,
#             alcaldia=user_info.alcaldia,
#             user_id=user_id
#         )
#         db.add(nueva_info)
#         db.commit()
#         db.refresh(nueva_info)

#         # Manejar la imagen si se proporcionó
#         if image:
#             # Validar extensión
#             allowed_extensions = {".jpg", ".jpeg", ".png"}
#             file_extension = os.path.splitext(image.filename)[1].lower()
#             if file_extension not in allowed_extensions:
#                 raise HTTPException(status_code=400, detail="Solo se permiten imágenes JPG o PNG")

#             # Asegurarse de que la carpeta exista
#             if not os.path.exists(UPLOAD_DIR):
#                 os.makedirs(UPLOAD_DIR)

#             # Generar un nombre único
#             unique_filename = f"{user_id}_{int(datetime.now().timestamp())}{file_extension}"
#             file_path = os.path.join(UPLOAD_DIR, unique_filename)

#             # Guardar la imagen
#             with open(file_path, "wb") as buffer:
#                 shutil.copyfileobj(image.file, buffer)

#             # Crear registro en image_user
#             nueva_imagen = ImageUser(
#                 file_name=unique_filename,
#                 file_path=file_path,
#                 user_info_id=nueva_info.id_user_info
#             )
#             db.add(nueva_imagen)
#             db.commit()
#             db.refresh(nueva_imagen)

#         return nueva_info

#     except json.JSONDecodeError:
#         raise  # Reenviar el error al endpoint
#     except ValidationError as e:
#         raise  # Reenviar el error al endpoint
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error creando información del usuario: {e}"
#         )

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

def actualizar_o_crear_user_info(
    user_id: int,
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    codigo_postal: Optional[int] = Form(None),
    ciudad: Optional[str] = Form(None),
    alcaldia: Optional[str] = Form(None),
    nombre_restaurante: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    image: UploadFile = None,
    db: Session = Depends(get_db)
):
    """
    Actualiza o crea la información del usuario autenticado.
    Los campos no enviados en el formulario se asignan como None.
    """
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
            whatsapp=whatsapp
        )
        db.add(user_info_record)
    
    db.commit()
    db.refresh(user_info_record)

    if image:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        file_path = f"static/uploadsUser/{image.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(image.file.read())
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