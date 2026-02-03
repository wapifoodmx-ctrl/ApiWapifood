
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
    },
    "PRUEBA_BASICO": {
        "amount": 400.0, # Usamos el monto del básico para referencia, o 0.0 si prefieres
        "currency": "MXN",
        "description": "Prueba Básico 15 Días",
        "duration_days": 15, # 👈 AQUÍ ESTÁ LA CLAVE
        "real_plan_name": "basico" # Mapeo al nombre real en BD para las mesas
    }
}


# class ActivatePlanInput(BaseModel):
#     email: EmailStr
#     plan: str  # Ejemplo: "BASICO", "INAUGURACION"

# @router.post("/activate-plan", status_code=status.HTTP_201_CREATED)
# async def activate_plan(
#     input: ActivatePlanInput = Body(...),
#     db: Session = Depends(get_db)
# ):
#     # 1. Validar Plan
#     plan_key = input.plan.upper()
#     plan_details = PLAN_PRICES.get(plan_key)

#     if not plan_details:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Plan '{input.plan}' no válido. Disponibles: {list(PLAN_PRICES.keys())}"
#         )
    
#     amount_to_charge = plan_details["amount"]
#     plan_name_to_db = plan_key.lower()

#     # 2. Buscar Usuario (Usamos ORM para tener el objeto completo)
#     user = db.query(User).filter(User.email == input.email).first()
#     if not user:
#         raise HTTPException(status_code=400, detail=f"No se encontró un usuario con el correo {input.email}")

#     # 3. Generar Datos de Pago
#     preference_id = f"free-{uuid.uuid4()}"
#     checkout_url = "https://wapifood.com/success" # URL dummy para plan gratuito
#     current_date = datetime.utcnow()
#     end_date = current_date + timedelta(days=30)

#     # 4. Insertar Pago (Usando Raw SQL como tenías, o podrías usar ORM)
#     # Mantenemos tu lógica de SQL puro para el pago
#     query = text("""
#     INSERT INTO payments (
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
    
#     values = {
#         "payment_method": "pasarela", # O "cortesia" / "gratis"
#         "amount": amount_to_charge,
#         "date": current_date,
#         "user_id": user.id_users,
#         "plan": plan_name_to_db,
#         "subscription_id": f"sub_free_{uuid.uuid4().hex[:8]}",
#         "status": "completed", # Importante: completed para que las mesas se generen
#         "checkout_session_id": None,
#         "email": input.email,
#         "subscription_end_date": end_date,
#         "mercado_pago_customer_id": "free_tier",
#         "mercado_pago_payment_id": None,
#         "mercado_pago_preapproval_id": None,
#         "checkout_url": checkout_url,
#         "mercado_pago_preference_id": preference_id
#     }

#     try:
#         db.execute(query, values)
#         db.commit() # Guardamos el pago PRIMERO para que las funciones de mesas lo encuentren
        
#         # ---------------------------------------------------------
#         # 🚀 EJECUCIÓN AUTOMÁTICA DE MESAS
#         # ---------------------------------------------------------
#         print(f"🔄 Generando mesas automáticamente para {user.email}...")
        
#         # A. Crear detalles de mesas (POST /tables/details)
#         # Pasamos el objeto 'user' que obtuvimos arriba
#         await create_table_details(db=db, current_user=user)
        
#         # B. Generar tablas físicas (POST /tables/generate)
#         await generate_tables_sub(db=db, current_user=user)
        
#         # C. Obtener estatus final (GET /tables/status)
#         # Nota: get_tables_status en tu código no es async, así que lo llamamos normal
#         status_mesas = get_tables_status(db=db, current_user=user)
        
#         # ---------------------------------------------------------

#         return {
#             "mensaje": f"Plan '{plan_name_to_db}' activado y mesas configuradas.",
#             "detalles_plan": {
#                 "email": input.email,
#                 "plan": plan_name_to_db,
#                 "vence": end_date.strftime('%Y-%m-%d')
#             },
#             "resumen_mesas": status_mesas # Retornamos el estatus de las mesas creadas
#         }

#     except Exception as e:
#         db.rollback()
#         print(f"❌ Error activando plan: {e}")
#         raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


class ActivatePlanInput(BaseModel):
    email: EmailStr
    plan: str  # Ejemplo: "PRUEBA_BASICO", "INAUGURACION"

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
    
    # Lógica para determinar el nombre del plan en BD
    # Si tiene 'real_plan_name' (como PRUEBA_BASICO), usamos ese. Si no, usamos el key en minúsculas.
    plan_name_to_db = plan_details.get("real_plan_name", plan_key.lower())
    
    # Lógica de Duración
    days_duration = plan_details.get("duration_days", 30) # Default 30 si no se especifica

    # 2. Buscar Usuario (Usamos ORM para tener el objeto completo)
    user = db.query(User).filter(User.email == input.email).first()
    if not user:
        raise HTTPException(status_code=400, detail=f"No se encontró un usuario con el correo {input.email}")

    # 3. Generar Datos de Pago
    preference_id = f"free-{uuid.uuid4()}"
    checkout_url = "https://wapifood.com/success" 
    current_date = datetime.utcnow()
    end_date = current_date + timedelta(days=days_duration) # 👈 Usamos la duración dinámica

    # 4. Insertar Pago
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
        "payment_method": "pasarela", # Diferenciamos que es prueba/cortesía
        "amount": amount_to_charge,
        "date": current_date,
        "user_id": user.id_users,
        "plan": plan_name_to_db, # Se guarda como "basico"
        "subscription_id": f"trial_{uuid.uuid4().hex[:8]}",
        "status": "completed",
        "checkout_session_id": None,
        "email": input.email,
        "subscription_end_date": end_date,
        "mercado_pago_customer_id": "trial_user",
        "mercado_pago_payment_id": None,
        "mercado_pago_preapproval_id": None,
        "checkout_url": checkout_url,
        "mercado_pago_preference_id": preference_id
    }

    try:
        db.execute(query, values)
        db.commit() 
        
        # ---------------------------------------------------------
        # 🚀 EJECUCIÓN AUTOMÁTICA DE MESAS
        # ---------------------------------------------------------
        print(f"🔄 Generando mesas automáticamente para {user.email}...")
        
        # A. Crear detalles de mesas (POST /tables/details)
        await create_table_details(db=db, current_user=user)
        
        # B. Generar tablas físicas (POST /tables/generate)
        await generate_tables_sub(db=db, current_user=user)
        
        # C. Obtener estatus final (GET /tables/status)
        status_mesas = get_tables_status(db=db, current_user=user)
        
        # ---------------------------------------------------------

        return {
            "mensaje": f"Plan de prueba '{plan_key}' activado por {days_duration} días.",
            "detalles_plan": {
                "email": input.email,
                "plan_db": plan_name_to_db,
                "duracion_dias": days_duration,
                "vence": end_date.strftime('%Y-%m-%d')
            },
            "resumen_mesas": status_mesas
        }

    except Exception as e:
        db.rollback()
        print(f"❌ Error activando plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")