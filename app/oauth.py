"""
Este módulo maneja la autenticación en FastAPI utilizando OAuth2 con contraseña (Bearer Token JWT).
Se basa en la documentación de FastAPI para OAuth2 con contraseña y tokens JWT.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.token import verify_token
from app.schemas import TokenData
# """
# Se define el esquema de autenticación OAuth2 con flujo de contraseña (password flow).
# El usuario debe enviar su token en la cabecera de autorización con formato Bearer.
# """
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Obtiene el usuario actual a partir de un token JWT.
    
    Parámetros:
    - token (str): Token de autenticación proporcionado en la solicitud HTTP.
    
    Retorna:
    - Usuario autenticado si el token es válido.
    
    Lanza:
    - HTTPException 401 si el token es inválido o no se puede validar.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    

