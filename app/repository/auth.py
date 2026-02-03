from sqlalchemy.orm import Session
from app.db import models
from fastapi import HTTPException, status
from app.hashing import Hash
from app.token import create_access_token
from datetime import timedelta
from app.token import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.db.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



def auth_user(usuario, db: Session):
    """
    Verifica correo y contraseña, y si son correctos, devuelve un Token Nuevo.
    """
    # 1. Buscar usuario
    user = db.query(models.User).filter(models.User.email == usuario.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario no encontrado con el email {usuario.email}"
        )
    
    # 2. Verificar Password
    if not Hash.verify_password(usuario.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta"
        )

    # 3. Crear Token
    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Función para verificar el token y obtener el usuario actual
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# # Esquema para obtener el token del encabezado Authorization
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

# def auth_user(usuario, db: Session):
#     user = db.query(models.User).filter(models.User.email == usuario.email).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Usuario no encontrado con el {usuario.email}"
#         )
#     if not Hash.verify_password(usuario.password, user.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Contraseña incorrecta"
#         )

#     access_token = create_access_token(
#         data={"sub": user.email}
#     )
#     return {"access_token": access_token, "token_type": "bearer"}

# # Función para verificar el token y obtener el usuario actual
# def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="No se pudo validar las credenciales",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         email: str = payload.get("sub")
#         if email is None:
#             raise credentials_exception
#     except JWTError:
#         raise credentials_exception
    
#     user = db.query(models.User).filter(models.User.email == email).first()
#     if user is None:
#         raise credentials_exception
#     return user
















""" def auth_user(usuario, db:Session):
    user = db.query(models.User).filter(models.User.email == usuario.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=fUsuario no encontrado con el {usuario.email}
        )
    #print("Este es la contraseña : ---->", Hash.verify_password(usuario.password, user.password))
    if not Hash.verify_password(usuario.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta"
        )

    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Función para verificar el token y obtener el usuario actual
def get_current_user(token: str, db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user """