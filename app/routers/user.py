from fastapi import APIRouter, Depends, status
from app.schemas import User, UserId, ShowUser
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


@router.delete('/{user_id}',  status_code=status.HTTP_200_OK)  # Eliminamos el usuario a partir del id
def eliminar_usuario(user_id: int, db: Session = Depends(get_db)):
    res = user.eliminar_usuario(user_id, db)
    return res

@router.put('/{user_id}', status_code=status.HTTP_200_OK)  # Actualizamos el usuario a partir del id
def actualizar_usuario(user_id: int, updateUser: User, db: Session = Depends(get_db)):  # Actualizamos el usuario a partir del id
    res = user.actualizar_usuarios(user_id,updateUser, db)
    return res