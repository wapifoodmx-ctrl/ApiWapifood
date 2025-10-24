from fastapi import APIRouter, Depends, status, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.db.database import get_db
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

router = APIRouter(
    prefix="/free",
    tags=["free"],
)


# Esquema para validar el input
class EmailInput(BaseModel):
    email: EmailStr  # Valida que el correo sea un formato válido

@router.post("/activate-plan", status_code=status.HTTP_201_CREATED)
async def activate_plan(
    input: EmailInput = Body(...),
    db: Session = Depends(get_db)
):
    # Buscar el user_id en la tabla users usando el email
    query_user = text("SELECT id_users FROM mydb.users WHERE email = :email")
    result = db.execute(query_user, {"email": input.email}).fetchone()
    
    if not result:
        raise HTTPException(status_code=400, detail=f"No se encontró un usuario con el correo {input.email}")
    
    user_id = result[0]  # Obtener el id_users

    # Generar ID único para mercado_pago_preference_id
    preference_id = f"246732687-{uuid.uuid4()}"
    checkout_url = f"https://www.mercadopago.com.mx/checkout/v1/redirect?pref_id={preference_id}"
    
    # Fechas (basado en la fecha actual: 14 de septiembre de 2025, 03:51 PM CST)
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Query SQL ajustada a la estructura de la tabla en producción
    query = text("""
        INSERT INTO mydb.payments (
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
        "payment_method": "pasarela",
        "amount": 100.00,
        "date": current_date,
        "user_id": user_id,
        "plan": "basico",
        "subscription_id": None,
        "status": "COMPLETED",
        "checkout_session_id": None,
        "email": input.email,
        "subscription_end_date": end_date,
        "mercado_pago_customer_id": "124240366747",
        "mercado_pago_payment_id": None,
        "mercado_pago_preapproval_id": None,
        "checkout_url": checkout_url,
        "mercado_pago_preference_id": preference_id
    }
    
    try:
        # Ejecutar la consulta
        db.execute(query, values)
        db.commit()
        
        return {
            "mensaje": f"Plan activado exitosamente para {input.email}",
            "detalles": {
                "email": input.email,
                "amount": 100.00,
                "plan": "basico",
                "subscription_end_date": end_date,
                "user_id": user_id
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al activar el plan: {str(e)}")