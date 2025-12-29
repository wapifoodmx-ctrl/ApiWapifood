from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
import re
import httpx
import os
from groq import AsyncGroq # <--- Usamos el cliente Asíncrono
from app.repository.auth import get_current_user
from app.db.models import User

# --- CONFIGURACIÓN ---
# Asegúrate de tener GROQ_API_KEY en tu .env
client = AsyncGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# URL del microservicio de inventario
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_API_URL", "https://api-micro.wapifood.com").rstrip("/")

# --- CEREBRO DEL BOT (Contexto) ---
WAPIFOOD_CONTEXTO = """
Eres WapiBot, el asistente virtual experto de la plataforma WapiFood.
Tu objetivo es ayudar a dueños de restaurantes, meseros y cocineros.
Responde de forma concisa, profesional y amable en español.

[INFORMACIÓN DE WAPIFOOD]
- Es una plataforma integral SaaS para restaurantes.
- Incluye: Menú digital QR, Punto de Venta (POS), Pantalla de Cocina (KDS), App de Meseros, Inventarios, Recetas y Analytics.
- Funciona en la nube: Compatible con cualquier PC, Tablet o Celular. No requiere instalación compleja.
- Precios: Planes accesibles desde básicos hasta empresariales. 0% comisiones por venta.
- Soporte: Técnico GRATUITO incluido.
- Integraciones: Compatible con impresoras térmicas bluetooth.
- Por el momento no tenemos importaciones de productos existentes desde otros sistemas.

[FUNCIONALIDADES CLAVE]
- Inventarios: Control de stock, recetas y mermas.
- Mesas: Mapa de mesas en tiempo real.
- Tickets: Generación de tickets digitales para ahorrar papel.
- Cocina: Comunicación instantánea entre meseros y cocina.
- Tickets: La conexion a impresoras bluetooth solo esta disponible en andriod.
- Tickets: En PC Selecionas el tamaño del ticket y lo ajustas al tamaño de tu impresora térmica.


[CONTACTO Y SOPORTE]
- Email: wapifoodmx@gmail.com
- Teléfono: +52 5520535967 (Lun-Vie 10am-6pm).

IMPORTANTE: Si el usuario pregunta por "stock" o "inventario" de un producto específico, dile que debe escribir el ID numérico del producto (Ejemplo: "dime el stock del producto 20").
"""

class RespuestaChat(BaseModel):
    respuesta: str

class PreguntaChat(BaseModel):
    pregunta: str

router = APIRouter()

@router.post("/", response_model=RespuestaChat)
async def handle_chatbot_query(
    pregunta_chat: PreguntaChat,
    request: Request, 
    current_user: User = Depends(get_current_user)
):
    pregunta = pregunta_chat.pregunta
    
    # =========================================================================
    # PASO 1: LÓGICA PRECISA (Inventario en tiempo real)
    # =========================================================================
    # Usamos regex porque Groq no tiene acceso a tu base de datos en tiempo real.
    if 'stock' in pregunta.lower() or 'inventario' in pregunta.lower():
        match = re.search(r'\b(\d+)\b', pregunta) # Busca un número (ID)
        
        if match:
            producto_id = match.group(1)
            
            # Obtener token del usuario para llamar al microservicio
            auth_header = request.headers.get('Authorization')
            headers = {"Authorization": auth_header}
            url = f"{INVENTORY_SERVICE_URL}/inventory/ingredients/{producto_id}"
            
            print(f"🤖 WapiBot consultando inventario: {url}")

            async with httpx.AsyncClient() as http_client:
                try:
                    resp = await http_client.get(url, headers=headers)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        nombre = data.get("name", "Producto")
                        stock = data.get("stock", 0)
                        unit = data.get("unit", "u")
                        # Retornamos respuesta directa, sin pasar por IA
                        return {"respuesta": f"📦 El stock actual de **{nombre}** (ID: {producto_id}) es de **{stock} {unit}**."}
                    
                    elif resp.status_code == 404:
                        return {"respuesta": f"❌ No encontré ningún producto con el ID {producto_id} en tu inventario."}
                
                except Exception as e:
                    print(f"⚠️ Error conectando al inventario: {e}")
                    # Si falla la conexión, dejamos que la IA intente responder algo genérico abajo.
                    pass 

    # =========================================================================
    # PASO 2: INTELIGENCIA ARTIFICIAL (Llama 3.3 vía Groq)
    # =========================================================================
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": WAPIFOOD_CONTEXTO
                },
                {
                    "role": "user",
                    "content": pregunta
                }
            ],
            model="llama-3.3-70b-versatile", # Tu modelo elegido
            temperature=0.3, # Bajo para que sea preciso y no invente
            max_completion_tokens=300, # Respuestas cortas y directas
            stream=False # IMPORTANTE: False para esperar la respuesta completa
        )

        respuesta_ia = chat_completion.choices[0].message.content
        return {"respuesta": respuesta_ia}

    except Exception as e:
        print(f"❌ Error Groq: {e}")
        # Fallback por si se acaban los créditos o falla la API
        return {"respuesta": "Lo siento, tengo problemas de conexión en este momento. Por favor contacta a soporte: wapifoodmx@gmail.com"}