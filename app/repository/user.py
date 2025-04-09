from sqlalchemy.orm import Session
from app.db import models
from app.schemas import User, UserId, UserInfo, RestauranteCreate, Restaurante
from fastapi import HTTPException, status
from app.hashing import Hash



def crear_usuario(usuario, db:Session()): 
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
              detail = f"Error creando usuario: {e}"
         )



def obtener_usuario(user_id, db:Session()):
    user = db.query(models.User).filter(models.User.id_users == user_id).first()
    if not user: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el usuario con el id {user_id}"
        )
    return user


def eliminar_usuario(user_id, db:Session()):
    user = db.query(models.User).filter(models.User.id_users == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return {"mensaje": "Usuario eliminado exitosamente"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Usuario no encontrado"
    )

def obtener_usuarios(db: Session()):  # Corrige el nombre aquí
    data = db.query(models.User).all()
    return data 

def actualizar_usuarios(user_id,updateUser, db:Session()):
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


# Nueva función para crear UserInfo
def crear_user_info(user_id: int, user_info: UserInfo, db: Session):
    try:
        # Verificar si ya existe un UserInfo para este usuario
        existing_info = db.query(models.UserInfo).filter(models.UserInfo.user_id == user_id).first()
        if existing_info:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe información personal para este usuario"
            )
        
        nueva_info = models.UserInfo(
            nombre=user_info.nombre,
            apellido=user_info.apellido,
            email=user_info.email,
            telefono=user_info.telefono,
            direccion=user_info.direccion,
            codigo_postal=user_info.codigo_postal,
            ciudad=user_info.ciudad,
            alcaldia=user_info.alcaldia,
            user_id=user_id
        )
        db.add(nueva_info)
        db.commit()
        db.refresh(nueva_info)
        return nueva_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Error creando información del usuario: {e}"
        )

# Nueva función para obtener User con UserInfo
def obtener_user_con_info(user_id: int, db: Session):
    user = db.query(models.User).filter(models.User.id_users == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el usuario con el id {user_id}"
        )
    return user  # La relación user_info se cargará automáticamente gracias a SQLAlchemy



def crear_restaurante(restaurante: RestauranteCreate, db: Session):
    try:
        nuevo_restaurante = models.Restaurante(
            nombre_restaurante=restaurante.nombre_restaurante,
            ciudad=restaurante.ciudad,
            estado_provincia=restaurante.estado_provincia,
            alcadia=restaurante.alcadia
        )
        db.add(nuevo_restaurante)
        db.commit()
        db.refresh(nuevo_restaurante)
        return nuevo_restaurante
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Error creando restaurante: {e}"
        )
