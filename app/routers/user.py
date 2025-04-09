from fastapi import APIRouter, Depends, status, HTTPException
from app.schemas import User, UserId, ShowUser, UserInfo, UserWithInfo, Restaurante, RestauranteCreate
from typing import List
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.db import models
from app.repository import user
from app.oauth import get_current_user


router = APIRouter(
    prefix="/user",
    tags=["User"],
)


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
def eliminar_usuario(user_id: int, db: Session = Depends(get_db)):
    res = user.eliminar_usuario(user_id, db)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {"mensaje": "Usuario eliminado exitosamente"}

# Actualizar un usuario
@router.put('/{user_id}', status_code=status.HTTP_200_OK, response_model=ShowUser)
def actualizar_usuario(user_id: int, updateUser: User, db: Session = Depends(get_db)):
    res = user.actualizar_usuarios(user_id, updateUser, db)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return res


# Nuevo endpoint para crear/actualizar UserInfo
@router.post("/{user_id}/info", status_code=status.HTTP_201_CREATED, response_model=UserInfo)
def crear_user_info(user_id: int, user_info: UserInfo, db: Session = Depends(get_db)):
    # Verificar si el usuario existe
    usuario = db.query(models.User).filter(models.User.id_users == user_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    # Crear la información personal
    nueva_info = user.crear_user_info(user_id, user_info, db)
    return nueva_info

# Nuevo endpoint para obtener User con UserInfo
@router.get("/{user_id}/info", response_model=UserWithInfo, status_code=status.HTTP_200_OK)
def obtener_user_con_info(user_id: int, db: Session = Depends(get_db)):
    usuario_con_info = user.obtener_user_con_info(user_id, db)
    if not usuario_con_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario_con_info


@router.post("/restaurante", status_code=status.HTTP_201_CREATED, response_model=Restaurante)
def crear_restaurante(restaurante: RestauranteCreate, db: Session = Depends(get_db)):
    nuevo_restaurante = user.crear_restaurante(restaurante, db)
    return nuevo_restaurante