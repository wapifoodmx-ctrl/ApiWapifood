"""
Este módulo maneja el hash y la verificación de contraseñas utilizando la librería passlib.
Se usa el algoritmo bcrypt para almacenar contraseñas de manera segura.
"""

from passlib.context import CryptContext

# """
# Se crea un contexto de cifrado con el algoritmo bcrypt.
# Se configura para manejar automáticamente la obsolescencia de algoritmos.
# """
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Hash:
    """
    Clase para manejar el hash y la verificación de contraseñas.
    """
    
    @staticmethod
    def hash_password(password: str):
        """
        Genera un hash seguro de la contraseña proporcionada.
        
        Parámetros:
        - password (str): La contraseña en texto plano que se va a cifrar.
        
        Retorna:
        - str: Contraseña cifrada con bcrypt.
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str):
        """
        Verifica si una contraseña en texto plano coincide con su versión hasheada.
        
        Parámetros:
        - plain_password (str): Contraseña en texto plano ingresada por el usuario.
        - hashed_password (str): Contraseña hasheada almacenada en la base de datos.
        
        Retorna:
        - bool: True si las contraseñas coinciden, False en caso contrario.
        
        Manejo de errores:
        - Si hashed_password es None o no es un string, retorna False.
        - Si ocurre un error al verificar (ejemplo: hash desconocido), también retorna False.
        """
        if not hashed_password or not isinstance(hashed_password, str):
            return False  # Si hashed_password es None o no es string, falla silenciosamente
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except ValueError:  # Captura UnknownHashError u otros errores de passlib
            return False
