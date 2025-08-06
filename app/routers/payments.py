from fastapi import APIRouter, HTTPException, Depends, Request, Form, status
from starlette.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import stripe
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import get_db
from app.db.models import Payments, User, TableDetails, Tables
from app.enums import PlanType, PaymentStatus
from app.repository.auth import get_current_user
from app.schemas import SubscriptionRequest
from typing import List
from app.enums import TablesEnum
from app.db.models import Tables as TablesModel, TableDetails, Payments
from app.enums import TablesEnum, SubscriptionAmount
from mercadopago import SDK 
import mercadopago

load_dotenv()
# stripe.api_key = os.getenv("STRIPE_API_KEY")
# stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# if not stripe.api_key:
#     raise ValueError("No se encontró la clave de API de Stripe en las variables de entorno")


# Configura Mercado Pago
mercado_pago_sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_ACCESS_TOKEN"))
mercado_pago_public_key = os.getenv("MERCADO_PAGO_PUBLIC_KEY")
mercado_pago_webhook_secret = os.getenv("MERCADO_PAGO_WEBHOOK_SECRET")

if not mercado_pago_sdk.access_token or not mercado_pago_public_key:
    raise ValueError("No se encontraron las credenciales de Mercado Pago en las variables de entorno")


router = APIRouter(
    prefix="/payments",
    tags=["payments"]
)

YOUR_DOMAIN = "http://127.0.0.1:8000"

# PLAN_PRICES = {
#     PlanType.BASICO: "price_1RMGJPAcLh3gfk7AeZCmoNOs" ,        #"prod_SGk7H4kqVBUvtP", # Reemplaza con el ID real del precio de Stripe
#     PlanType.PROFESIONAL: "price_1RMCjmAcLh3gfk7A4QwwMBLW",
#     PlanType.EMPRESARIAL: "price_1RMCkLAcLh3gfk7AkMlivuYU",
#     PlanType.BASICO_IMPRESORA: "price_1RmKjEAcLh3gfk7AErXZJ3I1",
#     PlanType.RESTAURANTE_IMPRESORA: "price_1RmKqcAcLh3gfk7ACUUqKfrK",
#     PlanType.PLUS_RESTAURANTE_IMPRESORA: "price_1RmKv3AcLh3gfk7A1ZGDGx90"
# }

# Mapa de precios para los planes
PLAN_PRICES = {
    PlanType.BASICO: {
        "amount": 100.0,
        "currency": "MXN",  # Ajusta según tu país (MXN, ARS, etc.)
        "description": "Plan Básico",
        "plan_id": None  # Se llenará dinámicamente
    },
    PlanType.PROFESIONAL: {
        "amount": 200.0,
        "currency": "MXN",
        "description": "Plan Profesional",
        "plan_id": None
    },
    PlanType.EMPRESARIAL: {
        "amount": 300.0,
        "currency": "MXN",
        "description": "Plan Empresarial",
        "plan_id": None
    },
    PlanType.BASICO_IMPRESORA: {
        "amount": 1960.0,
        "currency": "MXN",
        "description": "Plan Básico con Impresora",
        "plan_id": None
    },
    PlanType.RESTAURANTE_IMPRESORA: {
        "amount": 2920.0,
        "currency": "MXN",
        "description": "Plan Restaurante con Impresora",
        "plan_id": None
    },
    PlanType.PLUS_RESTAURANTE_IMPRESORA: {
        "amount": 3880.0,
        "currency": "MXN",
        "description": "Plan Plus Restaurante con Impresora",
        "plan_id": None
    }
}

#/ plan basico impresora : price_1RmKjEAcLh3gfk7AErXZJ3I1
#/ plan restaurante impresora : price_1RmKqcAcLh3gfk7ACUUqKfrK
#/ plan plu resturante impresora : price_1RmKv3AcLh3gfk7A1ZGDGx90  

#------------------------------------------
#----------------------------------price_1RMGJPAcLh3gfk7AeZCmoNOs es el id_del precio 

# Crear planes de suscripción al iniciar la aplicación
def create_mercado_pago_plans():
    for plan, details in PLAN_PRICES.items():
        try:
            response = mercado_pago_sdk.preapproval_plan().search(filters={"reason": details["description"]})
            existing_plans = response["response"]["results"]
            
            if existing_plans:
                print(f"Plan {details['description']} ya existe: {existing_plans[0]['id']}")
                PLAN_PRICES[plan]["plan_id"] = existing_plans[0]["id"]
            else:
                plan_data = {
                    "reason": details["description"],
                    "auto_recurring": {
                        "frequency": 1,
                        "frequency_type": "months" if plan in [PlanType.BASICO, PlanType.PROFESIONAL, PlanType.EMPRESARIAL] else "years",
                        "transaction_amount": float(details["amount"]),
                        "currency_id": details["currency"]
                    },
                    "back_url": f"{YOUR_DOMAIN}/payments/success",
                    "external_reference": f"plan_{plan.value}"
                }
                response = mercado_pago_sdk.preapproval_plan().create(plan_data)
                PLAN_PRICES[plan]["plan_id"] = response["response"]["id"]
                print(f"Plan creado: {details['description']} - ID: {response['response']['id']}")
        except Exception as e:
            print(f"Error al crear/verificar plan {plan}: {str(e)}")
            raise ValueError(f"Error al crear/verificar plan {plan}: {str(e)}")

create_mercado_pago_plans()

# Actualizar SubscriptionRequest
class SubscriptionRequest(BaseModel):
    plan: PlanType
    card_token: str  # Token de la tarjeta generado por el SDK de Mercado Pago

# Crear sesión de checkout
@router.post("/create-checkout-session")
async def create_checkout_session(
    subscription_request: SubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        plan_details = PLAN_PRICES.get(subscription_request.plan)
        if not plan_details or not plan_details.get("plan_id"):
            raise HTTPException(status_code=400, detail="Plan no válido o no configurado")

        # Crear cliente en Mercado Pago
        customer_data = {
            "email": current_user.email,
            "identification": {"type": "DNI", "number": "12345678"}  # Ajusta según tu caso
        }
        customer_response = mercado_pago_sdk.customer().create(customer_data)
        mercado_pago_customer_id = customer_response["response"]["id"]

        # Crear suscripción
        subscription_data = {
            "preapproval_plan_id": plan_details["plan_id"],
            "reason": plan_details["description"],
            "payer_email": current_user.email,
            "card_token": subscription_request.card_token,
            "external_reference": f"user_{current_user.id_users}",
            "back_url": f"{YOUR_DOMAIN}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months" if subscription_request.plan in [PlanType.BASICO, PlanType.PROFESIONAL, PlanType.EMPRESARIAL] else "years",
                "transaction_amount": float(plan_details["amount"]),
                "currency_id": plan_details["currency"]
            }
        }

        subscription_response = mercado_pago_sdk.preapproval().create(subscription_data)
        subscription = subscription_response["response"]

        # Calcular fecha de expiración
        current_date = datetime.utcnow()
        subscription_end_date = current_date + timedelta(days=365 if subscription_request.plan in [
            PlanType.BASICO_IMPRESORA,
            PlanType.RESTAURANTE_IMPRESORA,
            PlanType.PLUS_RESTAURANTE_IMPRESORA
        ] else 30)

        # Guardar pago
        payment = Payments(
            payment_method=PaymentMethodEnum.pasarela,
            amount=plan_details["amount"],
            date=datetime.utcnow(),
            subscription_end_date=subscription_end_date,
            user_id=current_user.id_users,
            mercado_pago_customer_id=mercado_pago_customer_id,
            mercado_pago_preapproval_id=subscription["id"],
            subscription_id=subscription["id"],
            checkout_session_id=subscription["id"],
            plan=subscription_request.plan,
            status=PaymentStatus.PENDING,
            email=current_user.email
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        print(f"Pago guardado: ID={payment.id_payments}, Preapproval ID={payment.mercado_pago_preapproval_id}")

        return JSONResponse(
            status_code=200,
            content={"checkout_url": subscription["init_point"]}
        )

    except Exception as e:
        print(f"Error al crear suscripción: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al crear suscripción: {str(e)}")

# Webhook
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
        event_type = payload.get("type")
        data = payload.get("data", {})

        print(f"Webhook recibido - Tipo: {event_type}, Datos: {data}")

        if event_type == "payment":
            payment_id = data.get("id")
            if not payment_id:
                print("No payment_id in event")
                return {"status": "ignored", "message": "No payment_id in event"}

            payment_response = mercado_pago_sdk.payment().get(payment_id)
            payment_data = payment_response["response"]

            preapproval_id = payment_data.get("preapproval_id")
            if not preapproval_id:
                print("No preapproval_id in payment")
                return {"status": "ignored", "message": "No preapproval_id in payment"}

            payment = db.query(Payments).filter(Payments.mercado_pago_preapproval_id == preapproval_id).first()
            if not payment:
                print(f"Pago no encontrado para preapproval_id: {preapproval_id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                print(f"Usuario no encontrado para user_id: {payment.user_id}")
                return {"status": "ignored", "message": "User not found"}

            payment.mercado_pago_payment_id = payment_id
            payment.amount = payment_data.get("transaction_amount", payment.amount)
            payment.status = PaymentStatus.COMPLETED if payment_data.get("status") == "approved" else PaymentStatus.FAILED
            payment.email = user.email

            days_to_add = 365 if payment.plan in [
                PlanType.BASICO_IMPRESORA,
                PlanType.RESTAURANTE_IMPRESORA,
                PlanType.PLUS_RESTAURANTE_IMPRESORA
            ] else 30
            try:
                if payment_data.get("date_approved"):
                    start_date = datetime.strptime(payment_data["date_approved"], "%Y-%m-%dT%H:%M:%S.%f%z")
                    subscription_end_date = start_date + timedelta(days=days_to_add)
                else:
                    subscription_end_date = datetime.utcnow() + timedelta(days=days_to_add)
                print(f"subscription_end_date: {subscription_end_date}")
            except Exception as e:
                print(f"Error al calcular subscription_end_date: {str(e)}")
                subscription_end_date = datetime.utcnow() + timedelta(days=days_to_add)

            payment.subscription_end_date = subscription_end_date
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.__dict__}")

            sync_tables_with_subscription(db, payment.user_id, payment.plan.value, payment.amount)

        elif event_type == "preapproval":
            preapproval_id = data.get("id")
            preapproval_response = mercado_pago_sdk.preapproval().get(preapproval_id)
            preapproval_data = preapproval_response["response"]

            payment = db.query(Payments).filter(Payments.mercado_pago_preapproval_id == preapproval_id).first()
            if not payment:
                print(f"Pago no encontrado para preapproval_id: {preapproval_id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                print(f"Usuario no encontrado para user_id: {payment.user_id}")
                return {"status": "ignored", "message": "User not found"}

            payment.status = PaymentStatus.COMPLETED if preapproval_data.get("status") == "authorized" else PaymentStatus.FAILED
            payment.email = user.email

            days_to_add = 365 if payment.plan in [
                PlanType.BASICO_IMPRESORA,
                PlanType.RESTAURANTE_IMPRESORA,
                PlanType.PLUS_RESTAURANTE_IMPRESORA
            ] else 30
            if preapproval_data.get("next_payment_date"):
                subscription_end_date = datetime.strptime(preapproval_data["next_payment_date"], "%Y-%m-%dT%H:%M:%S.%f%z")
                payment.subscription_end_date = subscription_end_date
            else:
                payment.subscription_end_date = datetime.utcnow() + timedelta(days=days_to_add)

            db.commit()
            db.refresh(payment)
            print(f"Suscripción actualizada: {payment.__dict__}")

            sync_tables_with_subscription(db, payment.user_id, payment.plan.value, payment.amount)

        elif event_type == "preapproval.canceled":
            preapproval_id = data.get("id")
            payment = db.query(Payments).filter(Payments.mercado_pago_preapproval_id == preapproval_id).first()
            if not payment:
                print(f"Pago no encontrado para preapproval_id: {preapproval_id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if user:
                payment.email = user.email

            payment.status = PaymentStatus.FAILED
            payment.subscription_end_date = None
            db.commit()
            db.refresh(payment)
            print(f"Suscripción cancelada: {payment.__dict__}")

            db.query(Tables).filter(Tables.user_id == payment.user_id).delete()
            db.query(TableDetails).filter(TableDetails.user_id == payment.user_id).delete()
            db.commit()
            print(f"Se eliminaron todas las mesas para el usuario {payment.user_id}")

        else:
            print(f"Evento no manejado: {event_type}")
            return {"status": "ignored", "message": f"Event type {event_type} not handled"}

        return {"status": "success"}

    except Exception as e:
        print(f"Error al procesar webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el evento: {str(e)}")

# Endpoint de éxito
@router.get("/success", status_code=status.HTTP_200_OK)
async def payment_success(request: Request, db: Session = Depends(get_db)):
    session_id = request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Falta el ID de la sesión")

    print(f"Procesando /success - Session ID: {session_id}")

    payment = db.query(Payments).filter(Payments.mercado_pago_preapproval_id == session_id).first()
    if not payment:
        print(f"Pago no encontrado para mercado_pago_preapproval_id: {session_id}")
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    user = db.query(User).filter(User.id_users == payment.user_id).first()
    if not user:
        print(f"Usuario no encontrado para user_id: {payment.user_id}")
        raise HTTPException(status_code=404, detail="Usuario asociado al pago no encontrado")

    try:
        preapproval = mercado_pago_sdk.preapproval().get(session_id)["response"]
        if preapproval["status"] == "authorized":
            payment.status = PaymentStatus.COMPLETED
            if preapproval.get("next_payment_date"):
                payment.subscription_end_date = datetime.strptime(preapproval["next_payment_date"], "%Y-%m-%dT%H:%M:%S.%f%z")
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.__dict__}")
    except Exception as e:
        print(f"Error al verificar suscripción: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al verificar suscripción: {str(e)}")

    subscription_end_date = payment.subscription_end_date.isoformat() if payment.subscription_end_date else None
    return {
        "message": "¡Suscripción creada con éxito!",
        "status": payment.status.value,
        "user_email": user.email,
        "subscription_end_date": subscription_end_date
    }

# Endpoint de cancelación
@router.get("/cancel", status_code=status.HTTP_200_OK)
async def payment_cancel():
    return {"message": "Suscripción cancelada."}

# Verificar pagos
@router.get("/check-payment")
async def check_payment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_email = current_user.email
    print(f"Buscando pagos para el correo: {user_email}")

    cutoff_date = datetime.utcnow() - timedelta(days=30)
    current_time = datetime.utcnow()

    payment = db.query(Payments).filter(
        Payments.email == user_email,
        Payments.date >= cutoff_date,
        Payments.status == PaymentStatus.COMPLETED,
        Payments.subscription_end_date != None,
        Payments.subscription_end_date > current_time
    ).order_by(Payments.date.desc()).first()

    if not payment:
        print("No se encontraron suscripciones activas")
        return {
            "message": "No se encontraron suscripciones activas en los últimos 30 días",
            "has_active_subscription": False
        }

    print(f"Suscripción activa encontrada: ID {payment.id_payments}, Fecha: {payment.date}, Plan: {payment.plan}")

    return {
        "message": "Última suscripción activa encontrada",
        "has_active_subscription": True,
        "payment": {
            "id": payment.id_payments,
            "amount": float(payment.amount),
            "date": payment.date.isoformat(),
            "plan": payment.plan.value,
            "status": payment.status.value,
            "subscription_end_date": payment.subscription_end_date.isoformat() if payment.subscription_end_date else None
        }
    }

# Obtener pagos del usuario
@router.get("/me", status_code=status.HTTP_200_OK, response_model=List[PaymentResponse])
async def get_user_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payments = db.query(Payments).filter(Payments.user_id == current_user.id_users).all()
    
    if not payments:
        raise HTTPException(status_code=404, detail="No se encontraron pagos para este usuario")

    return payments

# Sincronización de mesas
def sync_tables_with_subscription(db: Session, user_id: int, plan: str, amount: float):
    plan_mesas = {
        PlanType.BASICO.value: 1,
        PlanType.PROFESIONAL.value: 16,
        PlanType.EMPRESARIAL.value: 26,
        PlanType.BASICO_IMPRESORA.value: 1,
        PlanType.RESTAURANTE_IMPRESORA.value: 16,
        PlanType.PLUS_RESTAURANTE_IMPRESORA.value: 26
    }
    mesas_permitidas = plan_mesas.get(plan, 0)
    if mesas_permitidas == 0:
        raise HTTPException(status_code=400, detail="Plan no reconocido")

    amount_mapping = {
        100.0: SubscriptionAmount.PLAN_100,
        200.0: SubscriptionAmount.PLAN_200,
        300.0: SubscriptionAmount.PLAN_300,
        1960.0: SubscriptionAmount.BASICO_IMPRESORA,
        2920.0: SubscriptionAmount.RESTAURANTE_IMPRESORA,
        3880.0: SubscriptionAmount.PLUS_RESTAURANTE_IMPRESORA
    }
    try:
        subscription_amount_enum = amount_mapping.get(float(amount))
        if not subscription_amount_enum:
            raise ValueError(f"Monto {amount} no reconocido en amount_mapping")
        subscription_amount = subscription_amount_enum.value
        print(f"Subscription amount mapped to: {subscription_amount}")
    except (ValueError, TypeTypeError) as e:
        print(f"Error al mapear monto a SubscriptionAmount: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Monto {amount} no válido para SubscriptionAmount")

    try:
        mesas_actuales_details = db.query(TableDetails).filter(TableDetails.user_id == user_id).order_by(TableDetails.table_number).all()
        total_actuales_details = len(mesas_actuales_details)

        mesas_actuales_tables = db.query(Tables).filter(Tables.user_id == user_id).order_by(Tables.number).all()
        total_actuales_tables = len(mesas_actuales_tables)

        if total_actuales_details > mesas_permitidas:
            mesas_a_eliminar = mesas_actuales_details[mesas_permitidas:]
            for mesa in mesas_a_eliminar:
                db.delete(mesa)
            print(f"Se eliminaron {len(mesas_a_eliminar)} mesas sobrantes en TableDetails.")

        if total_actuales_tables > mesas_permitidas:
            mesas_a_eliminar = mesas_actuales_tables[mesas_permitidas:]
            for mesa in mesas_a_eliminar:
                db.delete(mesa)
            print(f"Se eliminaron {len(mesas_a_eliminar)} mesas sobrantes en Tables.")

        if total_actuales_details < mesas_permitidas:
            nuevas_mesas = []
            for i in range(total_actuales_details + 1, mesas_permitidas + 1):
                nuevas_mesas.append(
                    TableDetails(
                        user_id=user_id,
                        table_number=i,
                        estado=TablesEnum.Libre,
                        cantidad_ventas_por_mesa=0.0
                    )
                )
            db.add_all(nuevas_mesas)
            print(f"Se agregaron {len(nuevas_mesas)} nuevas mesas en TableDetails.")

        if total_actuales_tables < mesas_permitidas:
            nuevas_mesas = []
            for i in range(total_actuales_tables + 1, mesas_permitidas + 1):
                nuevas_mesas.append(
                    Tables(
                        number=i,
                        capacity=4,
                        state=TablesEnum.Libre,
                        user_id=user_id,
                        subscription_amount=subscription_amount
                    )
                )
            db.add_all(nuevas_mesas)
            print(f"Se agregaron {len(nuevas_mesas)} nuevas mesas en Tables.")

        db.commit()
        print(f"Sincronización completada: {mesas_permitidas} mesas para el usuario {user_id}")
        return {"message": f"Se han sincronizado {mesas_permitidas} mesas para el usuario", "mesas": mesas_permitidas}

    except Exception as e:
        db.rollback()
        print(f"Error al sincronizar mesas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al sincronizar mesas: {str(e)}")