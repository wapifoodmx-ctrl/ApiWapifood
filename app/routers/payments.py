from fastapi import APIRouter, HTTPException, Depends, Request, Form, status
from starlette.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import stripe
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import get_db
from app.db.models import Payments, User
from app.enums import PlanType, PaymentStatus
from app.repository.auth import get_current_user
from app.schemas import SubscriptionRequest


load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

if not stripe.api_key:
    raise ValueError("No se encontró la clave de API de Stripe en las variables de entorno")

router = APIRouter(
    prefix="/payments",
    tags=["payments"]
)

YOUR_DOMAIN = "http://127.0.0.1:8000"

PLAN_PRICES = {
    PlanType.BASICO: "price_1RMGJPAcLh3gfk7AeZCmoNOs" ,        #"prod_SGk7H4kqVBUvtP", # Reemplaza con el ID real del precio de Stripe
    PlanType.PROFESIONAL: "price_1RMCjmAcLh3gfk7A4QwwMBLW",
    PlanType.EMPRESARIAL: "price_1RMCkLAcLh3gfk7AkMlivuYU"
}

# Validar los price_id al iniciar la aplicación
for plan, price_id in PLAN_PRICES.items():
    if not price_id.startswith("price_"):
        raise ValueError(f"El ID para el plan {plan} debe ser un price_id (comenzar con 'price_'), no un product_id: {price_id}")
    try:
        price = stripe.Price.retrieve(price_id)
        if not price.recurring:
            raise ValueError(f"El price_id para el plan {plan} no es un precio recurrente: {price_id}. Debe ser un precio recurrente para usar mode='subscription'.")
    except stripe.error.InvalidRequestError as e:
        raise ValueError(f"El price_id para el plan {plan} no es válido o no existe en tu cuenta de Stripe: {price_id}. Error: {str(e)}")

@router.post("/create-checkout-session")
async def create_checkout_session(
    subscription_request: SubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        price_id = PLAN_PRICES.get(subscription_request.plan)
        if not price_id:
            raise HTTPException(status_code=400, detail="Plan no válido")

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {"price": price_id, "quantity": 1},
            ],
            mode="subscription",
            customer_email=current_user.email,
            success_url=YOUR_DOMAIN + "/payments/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=YOUR_DOMAIN + "/payments/cancel",
            metadata={"user_id": str(current_user.id_users)},
        )

        # Log antes de guardar el registro
        print(f"Checkout Session creada: ID={checkout_session.id}")
        print(f"Customer: {checkout_session.customer}")
        print(f"Subscription: {checkout_session.subscription}")
        print(f"URL: {checkout_session.url}")

        payment = Payments(
            payment_method="pasarela",
            amount=0,
            date=datetime.utcnow(),
            user_id=current_user.id_users,
            stripe_customer_id=checkout_session.customer,
            subscription_id=checkout_session.subscription,
            plan=subscription_request.plan.value,
            status=PaymentStatus.PENDING,
            checkout_session_id=checkout_session.id,
        )
        print(f"Registro a guardar: {payment.__dict__}")
        db.add(payment)
        try:
            db.commit()
            db.refresh(payment)
            print(f"Pago guardado: ID={payment.id_payments}, Checkout Session ID={payment.checkout_session_id}, Customer ID={payment.stripe_customer_id}, Subscription ID={payment.subscription_id}")
        except Exception as e:
            db.rollback()
            print(f"Error al guardar el pago: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al guardar el pago: {str(e)}")

        return JSONResponse(
            status_code=200,
            content={"checkout_url": checkout_session.url}
        )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")

@router.post("/create-portal-session", status_code=status.HTTP_303_SEE_OTHER)
async def create_portal_session(
    session_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        portal_session = stripe.billing_portal.Session.create(
            customer=checkout_session.customer,
            return_url=YOUR_DOMAIN,
        )
        return RedirectResponse(url=portal_session.url, status_code=303)

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, stripe_webhook_secret)
        print(f"Evento recibido: {event['type']} - ID: {event['id']}")
    except ValueError as e:
        print(f"Error en el payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Carga inválida")
    except stripe.error.SignatureVerificationError as e:
        print(f"Error en la firma: {str(e)}")
        raise HTTPException(status_code=400, detail="Firma inválida")

    try:
        if event["type"] == "checkout.session.completed":
            checkout_session = event["data"]["object"]
            subscription_id = checkout_session.get("subscription")
            print(f"Procesando checkout.session.completed - Subscription ID: {subscription_id}")

            if not subscription_id:
                print("No se encontró subscription_id en el evento")
                return {"status": "ignored", "message": "No subscription_id in event"}

            # Buscar el pago usando checkout_session_id
            payment = db.query(Payments).filter(Payments.checkout_session_id == checkout_session.id).first()
            if not payment:
                # Buscar por subscription_id o customer_id como respaldo
                payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment and checkout_session.customer:
                payment = db.query(Payments).filter(
                    Payments.stripe_customer_id == checkout_session.customer,
                    Payments.status == PaymentStatus.PENDING
                ).first()

            if not payment:
                print(f"No se encontró un pago con checkout_session_id: {checkout_session.id}, subscription_id: {subscription_id}, o customer_id: {checkout_session.customer}")
                return {"status": "ignored", "message": "Payment not found"}

            # Actualizar subscription_id y customer_id si no estaban disponibles inicialmente
            payment.subscription_id = subscription_id or payment.subscription_id
            payment.stripe_customer_id = checkout_session.customer or payment.stripe_customer_id

            # Obtener el monto de la suscripción desde Stripe
            subscription = stripe.Subscription.retrieve(subscription_id)
            amount = subscription.plan.amount / 100  # Convertir de centavos a dólares

            payment.status = PaymentStatus.COMPLETED
            payment.amount = amount
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.id_payments} - Estado: {payment.status} - Monto: {payment.amount}")

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")
            print(f"Procesando customer.subscription.deleted - Subscription ID: {subscription_id}")

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                print(f"No se encontró un pago con subscription_id: {subscription_id}")
                return {"status": "ignored", "message": "Payment not found"}

            payment.status = PaymentStatus.FAILED
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.id_payments} - Estado: {payment.status}")

        elif event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            subscription_id = payment_intent.get("metadata", {}).get("subscription_id")
            if not subscription_id:
                # Intentar obtener el subscription_id desde los cargos asociados
                if payment_intent.get("charges", {}).get("data"):
                    charge = payment_intent["charges"]["data"][0]
                    invoice_id = charge.get("invoice")
                    if invoice_id:
                        invoice = stripe.Invoice.retrieve(invoice_id)
                        subscription_id = invoice.get("subscription")

            if not subscription_id:
                print("No se encontró subscription_id en el payment_intent")
                return {"status": "ignored", "message": "No subscription_id in payment_intent"}

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                print(f"No se encontró un pago con subscription_id: {subscription_id}")
                return {"status": "ignored", "message": "Payment not found"}

            payment.stripe_payment_intent_id = payment_intent["id"]
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.id_payments} - Stripe Payment Intent ID: {payment.stripe_payment_intent_id}")

        else:
            print(f"Evento no manejado: {event['type']}")
            return {"status": "ignored", "message": f"Event type {event['type']} not handled"}

        return {"status": "success"}

    except Exception as e:
        print(f"Error al procesar el evento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el evento: {str(e)}")

@router.get("/success", status_code=status.HTTP_200_OK)
async def payment_success(request: Request, db: Session = Depends(get_db)):
    session_id = request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Falta el ID de la sesión")

    # Obtener la sesión de checkout para buscar el customer_id y subscription_id
    checkout_session = stripe.checkout.Session.retrieve(session_id)
    print(f"Procesando /success - Session ID: {session_id}, Customer: {checkout_session.customer}, Subscription: {checkout_session.subscription}")

    # Buscar el pago usando checkout_session_id
    payment = db.query(Payments).filter(Payments.checkout_session_id == session_id).first()
    print(f"Resultado de búsqueda por checkout_session_id ({session_id}): {payment}")
    
    if not payment and checkout_session.subscription:
        payment = db.query(Payments).filter(Payments.subscription_id == checkout_session.subscription).first()
        print(f"Resultado de búsqueda por subscription_id ({checkout_session.subscription}): {payment}")
    
    if not payment and checkout_session.customer:
        # Intentar buscar sin restringir por status, ya que el webhook podría haberlo actualizado
        payment = db.query(Payments).filter(Payments.stripe_customer_id == checkout_session.customer).first()
        print(f"Resultado de búsqueda por stripe_customer_id ({checkout_session.customer}): {payment}")

    if not payment:
        # Último intento: buscar por user_id desde los metadatos
        user_id = checkout_session.metadata.get("user_id")
        if user_id:
            payment = db.query(Payments).filter(
                Payments.user_id == int(user_id),
                Payments.checkout_session_id == session_id
            ).first()
            print(f"Resultado de búsqueda por user_id ({user_id}) y checkout_session_id: {payment}")

    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Validar que el usuario asociado al pago exista
    user = db.query(User).filter(User.id_users == payment.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario asociado al pago no encontrado")

    # Actualizar subscription_id si no estaba disponible
    if checkout_session.subscription and not payment.subscription_id:
        payment.subscription_id = checkout_session.subscription
        db.commit()
        db.refresh(payment)

    # Actualizar el estado si no está completado
    if payment.status != PaymentStatus.COMPLETED:
        payment.status = PaymentStatus.COMPLETED if checkout_session.payment_status == "paid" else PaymentStatus.FAILED
        db.commit()
        db.refresh(payment)

    return {"message": "¡Suscripción creada con éxito!", "status": payment.status, "user_email": user.email}

@router.get("/cancel", status_code=status.HTTP_200_OK)
async def payment_cancel():
    return {"message": "Suscripción cancelada."}

@router.get("/check-payment/{email}", status_code=status.HTTP_200_OK)
async def check_payment(email: str):
    try:
        customers = stripe.Customer.search(query=f"email:'{email}'")
        if not customers.data:
            return {"message": "No se encontró un cliente con ese correo", "has_paid": False}

        customer_id = customers.data[0].id
        thirty_days_ago = int((datetime.utcnow() - timedelta(days=30)).timestamp())

        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            created={"gte": thirty_days_ago},
            status="all"
        )
        if subscriptions.data:
            for subscription in subscriptions.data:
                if subscription.status in ["active", "trialing"]:
                    return {
                        "message": f"Cliente tiene una suscripción activa (ID: {subscription.id})",
                        "has_paid": True,
                        "subscription_id": subscription.id,
                        "status": subscription.status
                    }
                elif subscription.status == "canceled" and subscription.created >= thirty_days_ago:
                    invoices = stripe.Invoice.list(
                        subscription=subscription.id,
                        customer=customer_id,
                        created={"gte": thirty_days_ago}
                    )
                    for invoice in invoices.data:
                        if invoice.status == "paid":
                            return {
                                "message": f"Cliente realizó un pago relacionado con una suscripción cancelada (Invoice ID: {invoice.id})",
                                "has_paid": True,
                                "invoice_id": invoice.id
                            }

        payment_intents = stripe.PaymentIntent.list(
            customer=customer_id,
            created={"gte": thirty_days_ago}
        )
        if payment_intents.data:
            for intent in payment_intents.data:
                if intent.status == "succeeded":
                    return {
                        "message": f"Cliente realizó un pago único exitoso (PaymentIntent ID: {intent.id})",
                        "has_paid": True,
                        "payment_intent_id": intent.id
                    }

        return {"message": "No se encontraron pagos o suscripciones activas en los últimos 30 días", "has_paid": False}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")