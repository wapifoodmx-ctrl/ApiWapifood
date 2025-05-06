from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from enum import Enum
import stripe
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.db.models import Payments, User
from app.repository.auth import get_current_user
from app.enums import PlanType
from app.schemas import SubscriptionRequest

# Cargar variables de entorno
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Verificar que la clave se cargó correctamente
if not stripe.api_key:
    raise ValueError("No se encontró la clave de API de Stripe en las variables de entorno")

router = APIRouter(
    prefix="/payments",
    tags=["payments"]
)


# Diccionario con los precios de los planes (en dólares, convertiremos a centavos después)
PLAN_PRICES = {
    PlanType.BASICO: 29.99,
    PlanType.PROFESIONAL: 49.99,
    PlanType.EMPRESARIAL: 99.99
}

def get_plan_amount(plan: PlanType) -> int:
    """Obtiene el monto en centavos basado en el plan seleccionado."""
    amount_in_dollars = PLAN_PRICES.get(plan)
    if not amount_in_dollars:
        raise HTTPException(status_code=400, detail="Plan no válido")
    return int(amount_in_dollars * 100)  # Convertir a centavos

@router.post("/create-payment-intent")
async def create_payment(
    subscription_request: SubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un PaymentIntent con Stripe para el plan seleccionado, guarda el pago en la base de datos y devuelve el client_secret.
    """
    try:
        # Obtener el monto basado en el plan
        amount = get_plan_amount(subscription_request.plan)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero")

        # Crear el PaymentIntent en Stripe
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            automatic_payment_methods={"enabled": True},
        )

        # Guardar el pago en la base de datos
        payment = Payments(
            order_id=subscription_request.order_id,
            payment_method="pasarela",  # Usamos "pasarela" para Stripe
            amount=amount / 100,  # Convertimos de centavos a dólares para la base de datos
            date=datetime.utcnow(),
            user_id=current_user.id_users,
            stripe_payment_intent_id=intent["id"],
            plan=subscription_request.plan.value  # Guardamos el plan seleccionado (opcional, si tu modelo Payments lo soporta)
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {"clientSecret": intent["client_secret"]}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")