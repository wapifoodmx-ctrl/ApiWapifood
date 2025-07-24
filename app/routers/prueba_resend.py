import resend
from resend.exceptions import ResendError, InvalidApiKeyError
import logging
import os
import requests
from requests.exceptions import HTTPError

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configurar Resend
resend.api_key = os.getenv("RESEND_API_KEY", "re_UemXQYSm_4AWzQnvSrDtMzTmPvbdgqDEF")

try:
    headers = {
        "Authorization": f"Bearer {resend.api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "no-reply@wapifood.com",  # Usar dominio verificado
        "to": "moreno.jm730@gmail.com",
        "subject": "Prueba de Resend - WapiFood",
        "html": "<p>Prueba de envío de correo desde WapiFood</p>",
        "headers": {
            "List-Unsubscribe": "<mailto:unsubscribe@wapifood.com>",
            "X-Priority": "3"
        }
    }
    response = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers=headers
    )
    response.raise_for_status()
    logger.info(f"Correo enviado correctamente: {response.json()}")
    print(f"Correo enviado correctamente: {response.json()}")
except HTTPError as e:
    logger.error(f"Error HTTP al enviar correo: {str(e)}")
    logger.error(f"Respuesta de Resend: {e.response.text}")
    print(f"Error HTTP: {str(e)}")
    print(f"Respuesta de Resend: {e.response.text}")
except InvalidApiKeyError:
    logger.error("Clave API de Resend inválida")
    print("Error: Clave API inválida")
except ResendError as e:
    logger.error(f"Error de Resend: {str(e)}")
    print(f"Error de Resend: {str(e)}")
except Exception as e:
    logger.error(f"Error desconocido: {str(e)}")
    print(f"Error desconocido: {str(e)}")