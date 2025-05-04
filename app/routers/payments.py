from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import stripe
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.db.models import Payments, User
from app.repository.auth import get_current_user
from app.schemas import PaymentRequest, Item



# Cargar variables de entorno
load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Verificar que la clave se cargó correctamente (para depuración)
if not stripe.api_key:
    raise ValueError("No se encontró la clave de API de Stripe en las variables de entorno")

router = APIRouter(
    prefix="/payments",
    tags=["payments"]
)



def calculate_order_amount(items: List[Item]) -> int:
    """Calcula el monto total en centavos basado en los ítems."""
    total = sum(item.price * item.quantity for item in items)
    return total

@router.post("/create-payment-intent")
async def create_payment(
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un PaymentIntent con Stripe, guarda el pago en la base de datos y devuelve el client_secret.
    """
    try:
        amount = calculate_order_amount(payment_request.items)
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
            order_id=payment_request.order_id,
            payment_method="pasarela",  # Usamos "pasarela" para Stripe
            amount=amount / 100,  # Convertimos de centavos a dólares
            date=datetime.utcnow(),
            user_id=current_user.id_users,
            stripe_payment_intent_id=intent["id"]
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {"clientSecret": intent["client_secret"]}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")