"""
Este módulo maneja la generación y verificación de tokens JWT para autenticación.
Se utiliza la librería 'jose' para codificar y decodificar los tokens JWT.
"""

from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from app.schemas import TokenData
from fastapi import HTTPException, status

# """
# Clave secreta utilizada para firmar los tokens JWT.
# Debe mantenerse segura y nunca compartirse públicamente.
# """
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

# """
# Algoritmo de firma utilizado para la generación del token JWT.
# En este caso, se usa el algoritmo HS256 (HMAC con SHA-256).
# """
ALGORITHM = "HS256"

RESET_TOKEN_EXPIRE_MINUTES = 15  # Tiempo de expiración del token de restablecimiento en minutos

# """
# Tiempo de expiración del token en minutos.
# Define cuánto tiempo será válido un token antes de expirar.
# """
#ACCESS_TOKEN_EXPIRE_MINUTES = 30


# def create_access_token(data: dict):
#     """
#     Genera un token de acceso JWT a partir de un diccionario de datos.
    
#     Parámetros:
#     - data (dict): Información a codificar en el token.
    
#     Retorna:
#     - str: Token JWT generado.
#     """
#     to_encode = data.copy()
    
#     # """
#     # Calcula la fecha de expiración del token sumando el tiempo de expiración definido.
#     # """
#     # expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     # to_encode.update({"exp": expire})
    
    
#     # """
#     # Codifica los datos y genera el token JWT utilizando la clave secreta y el algoritmo definido.
#     # """
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt


# def verify_token(token: str):
#     """
#     Verifica y decodifica un token JWT para obtener los datos de usuario.
    
#     Parámetros:
#     - token (str): Token JWT a verificar.
    
#     Retorna:
#     - TokenData: Datos extraídos del token si es válido.
    
#     Lanza:
#     - JWTError: Si el token es inválido o está expirado.
#     """
#     try:
#         # """
#         # Decodifica el token JWT utilizando la clave secreta y el algoritmo especificado.
#         # """
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
#         # """
#         # Extrae el nombre de usuario del payload del token.
#         # """
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
        
#         # """
#         # Crea una instancia de TokenData con la información obtenida del token.
#         # """
#         token_data = TokenData(username=username)
#         return token_data
#     except JWTError:
#         raise credentials_exception



#CAMBIO PARA RESETEAR CONTRASEÑAS 



def create_access_token(data: dict, token_type: str = "access", expires_minutes: int = None):
    """
    Genera un token JWT (de acceso o restablecimiento) a partir de un diccionario de datos.
    
    Parámetros:
    - data (dict): Información a codificar en el token.
    - token_type (str): Tipo de token ('access' o 'reset').
    - expires_minutes (int): Minutos hasta la expiración (opcional, usa valor por defecto según tipo).
    
    Retorna:
    - str: Token JWT generado.
    """
    to_encode = data.copy()
    expire_minutes = expires_minutes or (RESET_TOKEN_EXPIRE_MINUTES if token_type == "reset" else 30)
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire, "token_type": token_type})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access"):
    """
    Verifica y decodifica un token JWT para obtener los datos de usuario.
    
    Parámetros:
    - token (str): Token JWT a verificar.
    - token_type (str): Tipo de token esperado ('access' o 'reset').
    
    Retorna:
    - TokenData: Datos extraídos del token si es válido.
    
    Lanza:
    - HTTPException: Si el token es inválido, está expirado o no coincide con el tipo esperado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type_received: str = payload.get("token_type")
        if username is None or token_type_received != token_type:
            raise credentials_exception
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        raise credentials_exception