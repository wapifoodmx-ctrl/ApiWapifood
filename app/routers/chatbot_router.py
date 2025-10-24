# Archivo: ./routers/chatbot_router.py

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
import re
from typing import Any
import httpx

# --- Importaciones de tu proyecto ---
### CAMBIO ###
# (Ajusta estas rutas de importación a la estructura de tu proyecto)
from sqlalchemy.orm import Session
from app.db.database import get_db  # Importa tu función get_db
from app.db.models import User       # Importa tu modelo Pydantic/SQLAlchemy 'User'
from app.repository.auth import get_current_user # ¡Importa tu función de autenticación real!
# --- Fin de Importaciones ---


# --- Modelos de Pydantic (sin cambios) ---
class RespuestaChat(BaseModel):
    respuesta: str

class PreguntaChat(BaseModel):
    pregunta: str

# ------------------------------------------------
# ### CAMBIO ### - URL de tu Microservicio
# ------------------------------------------------
# Define la URL base de tu servicio de inventario.
# (Cámbialo si está en producción o en otra IP/puerto)
INVENTORY_SERVICE_URL = "http://localhost:8001"

# ------------------------------------------------


# ------------------------------------------------
# Base de Conocimiento (sin cambios)
# ------------------------------------------------
intentos_bot = {
    'hola': 'SALUDO', 'gracias': 'AGRADECIMIENTO', 'adios': 'DESPEDIDA',
    'comanda': 'RASTREO_COMANDA', 'pago': 'INFO_PAGOS', 'tarjeta': 'INFO_PAGOS',
    'inventario': 'CONSULTA_INVENTARIO', 'stock': 'CONSULTA_INVENTARIO',
    'horario': 'INFO_HORARIO', 'contacto': 'INFO_CONTACTO',
}

respuestas_estaticas = {
    # Intención -> Respuesta directa
    'SALUDO': '¡Hola! 👋 ¿En qué puedo ayudarte hoy?',
    'AGRADECIMIENTO': '¡De nada! Estamos para servirte.',
    'DESPEDIDA': '¡Hasta luego! Que tengas un buen día.',
    'RASTREO_COMANDA': 'Puedes rastrear tu comanda usando tu número de orden aquí: https://wapifood.com/cocina',
    'INFO_PAGOS': 'Aceptamos tarjetas de crédito y débito. Puedes realizar pagos en: https://wapifood.com/payments.',
    'INFO_HORARIO': 'Nuestro horario de atención es de Lunes a Viernes, de 10:00 AM a 6:00 PM.',
    'INFO_CONTACTO': 'Puedes contactarnos directamente en wapitech.dev@gmail.com.',
    
    # Respuesta por defecto si no se extrae ID de inventario
    'DEFAULT_INVENTARIO': 'Para consultar el inventario, por favor dime el nombre o ID del producto (ej. "stock del producto 101").'
}

def identificar_intento(pregunta_usuario: str) -> str | None:
    pregunta = pregunta_usuario.lower()
    for palabra_clave, intento in intentos_bot.items():
        if palabra_clave in pregunta:
            return intento
    return None

# ------------------------------------------------
# 5. El Endpoint del Router (¡Llamando al Microservicio!)
# ------------------------------------------------

router = APIRouter()

@router.post("/", response_model=RespuestaChat)
async def handle_chatbot_query(
    pregunta_chat: PreguntaChat,
    
    ### CAMBIO ###
    # 1. Obtenemos el objeto 'Request' completo
    request: Request, 
    # 2. Obtenemos el usuario (para validar que esté autenticado)
    current_user: User = Depends(get_current_user)
    # (Ya no necesitamos 'db: Session' aquí, a menos que 'get_current_user' lo requiera)
):
    """
    Recibe una pregunta, la procesa llamando a otros servicios
    (con autenticación) y devuelve una respuesta.
    """
    
    pregunta = pregunta_chat.pregunta
    intento = identificar_intento(pregunta)
    
    # -----------------------------------
    # 2. Lógica Especial para INVENTARIO
    # -----------------------------------
    if intento == 'CONSULTA_INVENTARIO':
        match = re.search(r'\b(\d+)\b', pregunta) # Busca un ID numérico
        
        if match:
            producto_id = match.group(1)
            
            ### CAMBIO ### ¡Aquí ocurre la magia!
            
            # 1. Obtenemos el token de la solicitud original
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                # Esto no debería pasar si 'get_current_user' funcionó, pero por si acaso.
                raise HTTPException(status_code=401, detail="Falta cabecera de autenticación")

            headers = {"Authorization": auth_header}
            
            # 2. Construimos la URL del endpoint de inventario
            # Usamos el endpoint que nos diste: /inventory/ingredients/{ingredient_id}
            url = f"{INVENTORY_SERVICE_URL}/inventory/ingredients/{producto_id}"

            # 3. Hacemos la llamada HTTP asíncrona
            async with httpx.AsyncClient() as client:
                try:
                    # Hacemos el GET, reenviando la cabecera de autenticación
                    api_response = await client.get(url, headers=headers)
                    
                    # Lanza un error si la API devolvió 4xx o 5xx
                    api_response.raise_for_status() 

                except httpx.RequestError:
                    # Error de red (ej. el microservicio está caído)
                    return {"respuesta": "Lo siento, no puedo conectar con el servicio de inventario en este momento."}
                
                except httpx.HTTPStatusError as e:
                    # Error HTTP (ej. 404, 401, 500)
                    if e.response.status_code == 404:
                        return {"respuesta": f"Lo siento, no pude encontrar ningún producto con el ID {producto_id}."}
                    else:
                        # Otro error (ej. 500 en el microservicio, o 401 si el token falló allí)
                        return {"respuesta": f"Hubo un error al consultar el inventario (Error: {e.response.status_code})."}

            # 4. Procesamos la respuesta exitosa (HTTP 200)
            producto_data = api_response.json()

            # --- ¡IMPORTANTE! Asunciones ---
            # Estoy *asumiendo* que la respuesta de tu API de inventario
            # se ve así: {"name": "Pizza", "current_stock": 50}
            # ¡Ajusta "name" y "current_stock" a los nombres reales de tus campos!
            # ---------------------------------
            nombre_producto = producto_data.get("name", "Producto Desconocido")
            stock_producto = producto_data.get("stock") # O "stock", "quantity", etc.

            if stock_producto is not None:
                if stock_producto > 0:
                    respuesta = f"¡Encontrado! El stock de '{nombre_producto}' (ID: {producto_id}) es {stock_producto} unidades."
                else:
                    respuesta = f"El producto '{nombre_producto}' (ID: {producto_id}) está actualmente fuera de stock."
            else:
                respuesta = f"Encontré el producto '{nombre_producto}', pero no pude determinar su stock desde la API."
            
            return {"respuesta": respuesta}
        
        else:
            # No se proporcionó ID en la pregunta
            return {"respuesta": respuestas_estaticas['DEFAULT_INVENTARIO']}

    # -----------------------------------
    # 3. Lógica para respuestas estáticas
    # -----------------------------------
    elif intento in respuestas_estaticas:
        respuesta = respuestas_estaticas[intento]
        return {"respuesta": respuesta}

    # -----------------------------------
    # 4. Respuesta por Defecto
    # -----------------------------------
    else:
        return {"respuesta": "Lo siento, no entendí tu pregunta. ¿Puedes reformularla?"}