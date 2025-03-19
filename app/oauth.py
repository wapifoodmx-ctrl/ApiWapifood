"""
Este módulo maneja la autenticación en FastAPI utilizando OAuth2 con contraseña (Bearer Token JWT).
Se basa en la documentación de FastAPI para OAuth2 con contraseña y tokens JWT.
"""
from sqlalchemy.orm import Session
from app.db import models
from fastapi import HTTPException, status, Depends
from app.hashing import Hash
from app.token import create_access_token
from datetime import timedelta
from app.token import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from app.schemas import User
from app.db.database import get_db
# """
# Se define el esquema de autenticación OAuth2 con flujo de contraseña (password flow).
# El usuario debe enviar su token en la cabecera de autorización con formato Bearer.
# """
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token or token.count(".") != 2:
        raise credentials_exception

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
    return User.from_orm(user)

# def get_current_user(token: str = Depends(oauth2_scheme)):
#     """
#     Obtiene el usuario actual a partir de un token JWT.
    
#     Parámetros:
#     - token (str): Token de autenticación proporcionado en la solicitud HTTP.
    
#     Retorna:
#     - Usuario autenticado si el token es válido.
    
#     Lanza:
#     - HTTPException 401 si el token es inválido o no se puede validar.
#     """
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
    

