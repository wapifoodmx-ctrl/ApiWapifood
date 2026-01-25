
from fastapi import APIRouter, Depends, status, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.db.database import get_db
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from app.routers.tables import create_table_details, generate_tables_sub, get_tables_status
from app.db.models import User, Payments # Importamos los modelos
# Asumo que 'mercadopago' y 'MERCADO_PAGO_ACCESS_TOKEN' están definidos en otro lugar
# import mercadopago 
# from app.config import MERCADO_PAGO_ACCESS_TOKEN 

router = APIRouter(
    prefix="/free",  # Puedes considerar cambiar este prefijo si ya no es solo para "free"
    tags=["plans"],  # Cambié la etiqueta a "plans" (planes)
)

# --- INICIO DE DATOS DE EJEMPLO ---
# (Tus definiciones de planes, adaptadas para usar strings como claves)
# Asegúrate de tener esta definición accesible en este archivo.

PLAN_PRICES = {
    "INAUGURACION": {
        "amount": 40.0,
        "currency": "MXN",
        "description": "Plan de Inauguración (Promocional)"
    },
    "BASICO": {
        "amount": 400.0,
        "currency": "MXN",
        "description": "Plan Básico"
    },
    "PROFESIONAL": {
        "amount": 600.0,
        "currency": "MXN",
        "description": "Plan Profesional"
    },
    "EMPRESARIAL": {
        "amount": 800.0,
        "currency": "MXN",
        "description": "Plan Empresarial"
    },
    "BASICO_IMPRESORA": {
        "amount": 4000.0,
        "currency": "MXN",
        "description": "Plan Básico con Impresora"
    },
    "RESTAURANTE_IMPRESORA": {
        "amount": 6000.0,
        "currency": "MXN",
        "description": "Plan Restaurante con Impresora"
    },
    "PLUS_RESTAURANTE_IMPRESORA": {
        "amount": 8000.0,
        "currency": "MXN",
        "description": "Plan Plus Restaurante con Impresora"
    }
}
# --- FIN DE DATOS DE EJEMPLO ---


# MODIFICADO: Esquema para validar el input
# Ahora acepta tanto el email como el tipo de plan.
# class ActivatePlanInput(BaseModel):
#     email: EmailStr
#     plan: str  # Ejemplo: "BASICO", "PROFESIONAL", "INAUGURACION"


# @router.post("/activate-plan", status_code=status.HTTP_201_CREATED)
# async def activate_plan(
#     input: ActivatePlanInput = Body(...),  # MODIFICADO: Usa el nuevo esquema
#     db: Session = Depends(get_db)
# ):
    
#     # --- MODIFICADO: Validar el plan y obtener detalles ---
#     # Normalizamos el nombre del plan a mayúsculas para que coincida con las claves
#     plan_key = input.plan.upper() 
#     plan_details = PLAN_PRICES.get(plan_key)

#     if not plan_details:
#         # Si el plan no se encuentra en el diccionario, enviamos un error
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Plan '{input.plan}' no es válido. Planes disponibles: {list(PLAN_PRICES.keys())}"
#         )
    
#     # Obtenemos los valores dinámicos del plan
#     amount_to_charge = plan_details["amount"]
#     plan_name_to_db = plan_key.lower() # Convertimos a minúsculas para la BD (ej: "basico")
#     # --- FIN DE MODIFICACIÓN ---

#     # 1. Buscar el user_id (misma lógica que antes)
#     query_user = text("SELECT id_users FROM mydb.users WHERE email = :email")
#     result = db.execute(query_user, {"email": input.email}).fetchone()
#     if not result:
#         raise HTTPException(status_code=400, detail=f"No se encontró un usuario con el correo {input.email}")
#     user_id = result[0]

#     # 2. Generar IDs y Fechas (misma lógica que antes)
#     preference_id = f"246732687-{uuid.uuid4()}"
#     checkout_url = f"https://www.mercadopago.com.mx/checkout/v1/redirect?pref_id={preference_id}"
#     current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     # MODIFICADO: Usaremos 30 días como estándar, pero podrías hacerlo variable
#     # si agregas "duration_days" a tu diccionario PLAN_PRICES.
#     end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

#     # 3. Preparar la consulta SQL (la consulta no cambia)
#     query = text("""
#     INSERT INTO mydb.payments (
#         payment_method, amount, date, user_id, plan, subscription_id,
#         status, checkout_session_id, email, subscription_end_date,
#         mercado_pago_customer_id, mercado_pago_payment_id,
#         mercado_pago_preapproval_id, checkout_url, mercado_pago_preference_id
#     ) VALUES (
#         :payment_method, :amount, :date, :user_id, :plan, :subscription_id,
#         :status, :checkout_session_id, :email, :subscription_end_date,
#         :mercado_pago_customer_id, :mercado_pago_payment_id,
#         :mercado_pago_preapproval_id, :checkout_url, :mercado_pago_preference_id
#     )
#     """)
    
#     # 4. MODIFICADO: Valores para la consulta
#     # Usamos las variables dinámicas 'amount_to_charge' y 'plan_name_to_db'
#     values = {
#         "payment_method": "pasarela",
#         "amount": amount_to_charge,         # <-- CAMBIADO
#         "date": current_date,
#         "user_id": user_id,
#         "plan": plan_name_to_db,           # <-- CAMBIADO
#         "subscription_id": None,
#         "status": "COMPLETED",             # Asumimos COMPLETED para esta simulación
#         "checkout_session_id": None,
#         "email": input.email,
#         "subscription_end_date": end_date,
#         "mercado_pago_customer_id": "124240366747", # (Dato de ejemplo)
#         "mercado_pago_payment_id": None,
#         "mercado_pago_preapproval_id": None,
#         "checkout_url": checkout_url,
#         "mercado_pago_preference_id": preference_id
#     }

#     # 5. Ejecutar y confirmar (misma lógica que antes)
#     try:
#         db.execute(query, values)
#         db.commit()
        
#         # MODIFICADO: Respuesta dinámica
#         return {
#             "mensaje": f"Plan '{plan_name_to_db}' activado exitosamente para {input.email}",
#             "detalles": {
#                 "email": input.email,
#                 "amount": amount_to_charge,
#                 "plan": plan_name_to_db,
#                 "subscription_end_date": end_date,
#                 "user_id": user_id
#             }
#         }
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Error al activar el plan: {str(e)}")



class ActivatePlanInput(BaseModel):
    email: EmailStr
    plan: str  # Ejemplo: "BASICO", "INAUGURACION"

@router.post("/activate-plan", status_code=status.HTTP_201_CREATED)
async def activate_plan(
    input: ActivatePlanInput = Body(...),
    db: Session = Depends(get_db)
):
    # 1. Validar Plan
    plan_key = input.plan.upper()
    plan_details = PLAN_PRICES.get(plan_key)

    if not plan_details:
        raise HTTPException(
            status_code=400, 
            detail=f"Plan '{input.plan}' no válido. Disponibles: {list(PLAN_PRICES.keys())}"
        )
    
    amount_to_charge = plan_details["amount"]
    plan_name_to_db = plan_key.lower()

    # 2. Buscar Usuario (Usamos ORM para tener el objeto completo)
    user = db.query(User).filter(User.email == input.email).first()
    if not user:
        raise HTTPException(status_code=400, detail=f"No se encontró un usuario con el correo {input.email}")

    # 3. Generar Datos de Pago
    preference_id = f"free-{uuid.uuid4()}"
    checkout_url = "https://wapifood.com/success" # URL dummy para plan gratuito
    current_date = datetime.utcnow()
    end_date = current_date + timedelta(days=30)

    # 4. Insertar Pago (Usando Raw SQL como tenías, o podrías usar ORM)
    # Mantenemos tu lógica de SQL puro para el pago
    query = text("""
    INSERT INTO payments (
        payment_method, amount, date, user_id, plan, subscription_id,
        status, checkout_session_id, email, subscription_end_date,
        mercado_pago_customer_id, mercado_pago_payment_id,
        mercado_pago_preapproval_id, checkout_url, mercado_pago_preference_id
    ) VALUES (
        :payment_method, :amount, :date, :user_id, :plan, :subscription_id,
        :status, :checkout_session_id, :email, :subscription_end_date,
        :mercado_pago_customer_id, :mercado_pago_payment_id,
        :mercado_pago_preapproval_id, :checkout_url, :mercado_pago_preference_id
    )
    """)
    
    values = {
        "payment_method": "pasarela", # O "cortesia" / "gratis"
        "amount": amount_to_charge,
        "date": current_date,
        "user_id": user.id_users,
        "plan": plan_name_to_db,
        "subscription_id": f"sub_free_{uuid.uuid4().hex[:8]}",
        "status": "completed", # Importante: completed para que las mesas se generen
        "checkout_session_id": None,
        "email": input.email,
        "subscription_end_date": end_date,
        "mercado_pago_customer_id": "free_tier",
        "mercado_pago_payment_id": None,
        "mercado_pago_preapproval_id": None,
        "checkout_url": checkout_url,
        "mercado_pago_preference_id": preference_id
    }

    try:
        db.execute(query, values)
        db.commit() # Guardamos el pago PRIMERO para que las funciones de mesas lo encuentren
        
        # ---------------------------------------------------------
        # 🚀 EJECUCIÓN AUTOMÁTICA DE MESAS
        # ---------------------------------------------------------
        print(f"🔄 Generando mesas automáticamente para {user.email}...")
        
        # A. Crear detalles de mesas (POST /tables/details)
        # Pasamos el objeto 'user' que obtuvimos arriba
        await create_table_details(db=db, current_user=user)
        
        # B. Generar tablas físicas (POST /tables/generate)
        await generate_tables_sub(db=db, current_user=user)
        
        # C. Obtener estatus final (GET /tables/status)
        # Nota: get_tables_status en tu código no es async, así que lo llamamos normal
        status_mesas = get_tables_status(db=db, current_user=user)
        
        # ---------------------------------------------------------

        return {
            "mensaje": f"Plan '{plan_name_to_db}' activado y mesas configuradas.",
            "detalles_plan": {
                "email": input.email,
                "plan": plan_name_to_db,
                "vence": end_date.strftime('%Y-%m-%d')
            },
            "resumen_mesas": status_mesas # Retornamos el estatus de las mesas creadas
        }

    except Exception as e:
        db.rollback()
        print(f"❌ Error activando plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")