from fastapi import APIRouter, Depends
from app.schemas import User, UserId
from typing import List
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.db import models



#Se crean las listas de los usuarios, ordenes, mesas, productos, detalles de ordenes y pagos
#Para poder almacenar los datos temporales en la base de datos de la memoria
usuarios: List[User] = []

 
router = APIRouter(
      prefix="/user",
      tags=["User"],
)


@router.get("/") #Del diccioanrio que creamos se guardan los ususaarios creados 
def obtener_usuarios(db: Session = Depends(get_db)):
    data = db.query(models.User).all()
    return data

@router.post("/") #AL crear los usuarios nos muestra un mensaje 
def crear_usuario(user:User):
    usuario = user.dict()
    usuarios.append(usuario)
    return {"mensaje": "Usuario creado exitosamente"}

@router.post('/{user_id}') #Post para obtener el usuario apartir del id 
def obtener_usuario(user_id:int):
    for user in usuarios:
        if user["id_users"] == user_id:
            return {"usuario":user}
    return {"mensaje": "Usuario no encontrado"}


@router.post('/obtener_usuario2') #Obtenemos el usuario apartir del id
def Obtener_usuario(user_id:UserId):
    for user in usuarios:
        if user["id_users"] == user_id.id_user:
            return {"usuario":user}
    return {"mensaje": "Usuario no encontrado"}

@router.delete('/{user_id}') #Eliminamos el usuario apartir del id
def eliminar_usuario(user_id:int):
    for index, user in enumerate(usuarios):#Se recorre el indice y el usuario
        if user["id_users"] == user_id:
            usuarios.pop(index) #el pop hace que se elimine el usuario en el indice
            return {"mensaje": "Usuario eliminado exitosamente"}
    return {"mensaje": "Usuario no encontrado"}


@router.put('/{user_id}') #Actualizamos el usuario apartir del id
def actualizar_usuario(user_id:int, updateUser:User): #Actualizamos el usuario apartir del id
    for index, user in enumerate(usuarios):#Se recorre el indice y el usuario
        if user["id_users"] == user_id:#Si el usuario es igual al id del usuario
            usuarios[index]["id_user"] = updateUser.name.dict()["id_user"]
            usuarios[index]["name"] = updateUser.name.dict()["name"]
            usuarios[index]["email"] = updateUser.name.dict()["email"]
            usuarios[index]["password"] = updateUser.name.dict()["password"]
            usuarios[index]["rol"] = updateUser.name.dict()["rol"]
            #Se actualiza el nombre
            return {"mensaje": "Usuario actualizado exitosamente"}
    return {"mensaje": "Usuario no encontrado"}
