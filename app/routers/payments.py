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
from typing import List

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

        # Crear un cliente de Stripe si no existe
        customer = stripe.Customer.create(email=current_user.email)
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {"price": price_id, "quantity": 1},
            ],
            mode="subscription",
            customer=customer.id,
            success_url="http://192.168.1.71:3000/success/?session_id={CHECKOUT_SESSION_ID}",
            #success_url=YOUR_DOMAIN + "/payments/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://192.168.1.71:3000/error",
            #cancel_url=YOUR_DOMAIN + "/payments/cancel",
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
            email=current_user.email, # Guardar el email del usuario
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

@router.post("/create-portal-session", status_code=status.HTTP_200_OK)  # Cambia a 200
async def create_portal_session(
    session_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Obtener el checkout_session para extraer el stripe_customer_id
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        stripe_customer_id = checkout_session.customer

        if not stripe_customer_id:
            raise HTTPException(status_code=400, detail="No se encontró stripe_customer_id en la sesión")

        # Crear la sesión del portal
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url="http://127.0.0.1:8000",
        )

        # Devolver JSON en lugar de redirigir
        return {"portal_url": portal_session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, stripe_webhook_secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Carga inválida")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Firma inválida")

    try:
        if event["type"] == "checkout.session.completed":
            checkout_session = event["data"]["object"]
            subscription_id = checkout_session.get("subscription")

            if not subscription_id:
                return {"status": "ignored", "message": "No subscription_id in event"}

            payment = db.query(Payments).filter(Payments.checkout_session_id == checkout_session.id).first()
            if not payment:
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                return {"status": "ignored", "message": "User not found"}

            payment.subscription_id = subscription_id or payment.subscription_id
            payment.stripe_customer_id = checkout_session.customer or payment.stripe_customer_id

            subscription = stripe.Subscription.retrieve(subscription_id)
            print(f"Subscription retrieved: {subscription}")
            print(f"Subscription Current Period End: {subscription.current_period_end}")

            if subscription.plan and subscription.plan.amount:
                amount = subscription.plan.amount / 100
            else:
                price_id = subscription.plan.id if subscription.plan else None
                if price_id:
                    price = stripe.Price.retrieve(price_id)
                    amount = price.unit_amount / 100
                else:
                    amount = 0
            payment.amount = amount
            print(f"Amount set to: {amount}")

            if subscription.current_period_end:
                subscription_end_date = datetime.utcfromtimestamp(subscription.current_period_end)
                print(f"Subscription end date from current_period_end: {subscription_end_date}")
            else:
                if subscription.current_period_start and subscription.plan and subscription.plan.interval:
                    start_date = datetime.utcfromtimestamp(subscription.current_period_start)
                    if subscription.plan.interval == "month":
                        subscription_end_date = start_date + timedelta(days=30)
                    elif subscription.plan.interval == "year":
                        subscription_end_date = start_date + timedelta(days=365)
                    else:
                        subscription_end_date = start_date + timedelta(days=30)
                    print(f"Subscription end date calculated from start: {subscription_end_date}")
                else:
                    subscription_end_date = datetime.utcnow() + timedelta(days=30)
                    print(f"Subscription end date calculated manually: {subscription_end_date}")
            payment.subscription_end_date = subscription_end_date
            print(f"Subscription end date saved: {payment.subscription_end_date}")

            payment.status = PaymentStatus.COMPLETED
            payment.email = user.email
            db.commit()
            db.refresh(payment)
            print(f"Payment updated in DB: {payment.__dict__}")

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                return {"status": "ignored", "message": "User not found"}

            # Actualizar el monto si cambió el plan
            if subscription.plan and subscription.plan.amount:
                amount = subscription.plan.amount / 100
                payment.amount = amount
                print(f"Updated amount to: {amount}")

            # Actualizar la fecha de finalización
            if subscription.current_period_end:
                subscription_end_date = datetime.utcfromtimestamp(subscription.current_period_end)
                payment.subscription_end_date = subscription_end_date
                print(f"Updated subscription end date to: {subscription_end_date}")
            else:
                if subscription.current_period_start and subscription.plan and subscription.plan.interval:
                    start_date = datetime.utcfromtimestamp(subscription.current_period_start)
                    if subscription.plan.interval == "month":
                        subscription_end_date = start_date + timedelta(days=30)
                    elif subscription.plan.interval == "year":
                        subscription_end_date = start_date + timedelta(days=365)
                    else:
                        subscription_end_date = start_date + timedelta(days=30)
                    payment.subscription_end_date = subscription_end_date
                    print(f"Calculated subscription end date: {subscription_end_date}")
                else:
                    payment.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                    print(f"Manually set subscription end date: {payment.subscription_end_date}")

            # Actualizar el estado si es necesario (por ejemplo, si se reactiva)
            if subscription.status == "active" or subscription.status == "trialing":
                payment.status = PaymentStatus.COMPLETED
            elif subscription.status == "canceled":
                payment.status = PaymentStatus.FAILED
            payment.email = user.email
            db.commit()
            db.refresh(payment)
            print(f"Payment updated in DB: {payment.__dict__}")

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if user:
                payment.email = user.email

            payment.status = PaymentStatus.FAILED
            payment.subscription_end_date = None  # Limpia la fecha de finalización
            db.commit()
            db.refresh(payment)
            print(f"Payment canceled in DB: {payment.__dict__}")

        elif event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            subscription_id = payment_intent.get("metadata", {}).get("subscription_id")
            if not subscription_id:
                if payment_intent.get("charges", {}).get("data"):
                    charge = payment_intent["charges"]["data"][0]
                    invoice_id = charge.get("invoice")
                    if invoice_id:
                        invoice = stripe.Invoice.retrieve(invoice_id)
                        subscription_id = invoice.get("subscription")

            if not subscription_id:
                return {"status": "ignored", "message": "No subscription_id in payment_intent"}

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if user:
                payment.email = user.email

            payment.stripe_payment_intent_id = payment_intent["id"]
            db.commit()
            db.refresh(payment)

        else:
            return {"status": "ignored", "message": f"Event type {event['type']} not handled"}

        return {"status": "success"}

    except Exception as e:
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
        payment = db.query(Payments).filter(Payments.stripe_customer_id == checkout_session.customer).first()
        print(f"Resultado de búsqueda por stripe_customer_id ({checkout_session.customer}): {payment}")

    if not payment:
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

    return {"message": "¡Suscripción creada con éxito!", "status": payment.status.value, "user_email": user.email}

@router.get("/cancel", status_code=status.HTTP_200_OK)
async def payment_cancel():
    return {"message": "Suscripción cancelada."}

#-----------------------------------------------------------------
#-----------------------------------------------------------------


@router.get("/check-payment/{email}")
async def check_payment(email: str, db: Session = Depends(get_db)):
    # Decodificar el correo
    decoded_email = email.replace("%40", "@")
    print(f"Buscando pagos para el correo: {decoded_email}")

    # Definir el límite de 30 días
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    print(f"Fecha límite para los pagos: {cutoff_date}")

    # Fecha actual para verificar suscripciones activas
    current_time = datetime.utcnow()
    print(f"Fecha actual: {current_time}")

    # Buscar la última suscripción activa
    payment = db.query(Payments).filter(
        Payments.email == decoded_email,
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
            "amount": payment.amount,
            "date": payment.date.isoformat(),
            "plan": payment.plan,
            "status": payment.status,
            "subscription_end_date": payment.subscription_end_date.isoformat() if payment.subscription_end_date else None
        }
    }

#-----------------------------------------------------------------
#-----------------------------------------------------------------



@router.get("/success/{session_id}", status_code=status.HTTP_200_OK)
async def payment_success(
    session_id: str,
    db: Session = Depends(get_db)
):
    print(f"Recibido session_id en /success: {session_id}")

    # Validar que session_id no esté vacío
    if not session_id:
        print("Error: session_id está vacío")
        raise HTTPException(status_code=400, detail="Falta el ID de la sesión")

    # Obtener la sesión de checkout para buscar el customer_id y subscription_id
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        print(f"Procesando /success - Session ID: {session_id}, Customer: {checkout_session.customer}, Subscription: {checkout_session.subscription}")
    except stripe.error.InvalidRequestError as e:
        print(f"Error al recuperar la sesión de Stripe: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al recuperar la sesión de Stripe: {str(e)}")

    # Buscar el pago usando checkout_session_id
    payment = db.query(Payments).filter(Payments.checkout_session_id == session_id).first()
    print(f"Resultado de búsqueda por checkout_session_id ({session_id}): {payment}")
    
    if not payment and checkout_session.subscription:
        payment = db.query(Payments).filter(Payments.subscription_id == checkout_session.subscription).first()
        print(f"Resultado de búsqueda por subscription_id ({checkout_session.subscription}): {payment}")
    
    if not payment and checkout_session.customer:
        payment = db.query(Payments).filter(Payments.stripe_customer_id == checkout_session.customer).first()
        print(f"Resultado de búsqueda por stripe_customer_id ({checkout_session.customer}): {payment}")

    if not payment:
        user_id = checkout_session.metadata.get("user_id")
        if user_id:
            payment = db.query(Payments).filter(
                Payments.user_id == int(user_id),
                Payments.checkout_session_id == session_id
            ).first()
            print(f"Resultado de búsqueda por user_id ({user_id}) y checkout_session_id: {payment}")

    if not payment:
        print("Error: No se encontró el pago después de todas las búsquedas")
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Validar que el usuario asociado al pago exista
    user = db.query(User).filter(User.id_users == payment.user_id).first()
    if not user:
        print(f"Error: No se encontró el usuario asociado al pago (user_id: {payment.user_id})")
        raise HTTPException(status_code=404, detail="Usuario asociado al pago no encontrado")

    # Actualizar subscription_id si no estaba disponible
    if checkout_session.subscription and not payment.subscription_id:
        payment.subscription_id = checkout_session.subscription
        db.commit()
        db.refresh(payment)
        print(f"subscription_id actualizado: {payment.subscription_id}")

    # Actualizar el estado si no está completado
    if payment.status != PaymentStatus.COMPLETED:
        payment.status = PaymentStatus.COMPLETED if checkout_session.payment_status == "paid" else PaymentStatus.FAILED
        db.commit()
        db.refresh(payment)
        print(f"Estado actualizado: {payment.status}")

    # Preparar la fecha de finalización para la respuesta
    subscription_end_date = payment.subscription_end_date.isoformat() if payment.subscription_end_date else None

    print("Pago encontrado, devolviendo respuesta")
    return {
        "message": "¡Suscripción creada con éxito!",
        "status": payment.status.value,
        "user_email": user.email,
        "subscription_end_date": subscription_end_date
    }

#--------------------------------------------------------------------
#--------------------------------------------------------------------

# Nuevo endpoint para obtener los pagos del usuario autenticado
@router.get("/me", status_code=status.HTTP_200_OK, response_model=List[dict])
async def get_user_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Buscar todos los pagos asociados al user_id del usuario autenticado
    payments = db.query(Payments).filter(Payments.user_id == current_user.id_users).all()
    
    if not payments:
        raise HTTPException(status_code=404, detail="No se encontraron pagos para este usuario")

    # Preparar la lista de pagos con los datos formateados
    payment_details = []
    for payment in payments:
        date = payment.date.isoformat() if payment.date else None
        subscription_end_date = payment.subscription_end_date.isoformat() if payment.subscription_end_date else None
        payment_details.append({
            "id_payments": payment.id_payments,
            "payment_method": payment.payment_method,
            "amount": payment.amount,
            "date": date,
            "user_id": payment.user_id,
            "plan": payment.plan.value if payment.plan else None,
            "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            "stripe_customer_id": payment.stripe_customer_id,
            "subscription_id": payment.subscription_id,
            "status": payment.status.value if payment.status else None,
            "checkout_session_id": payment.checkout_session_id,
            "email": payment.email,
            "subscription_end_date": subscription_end_date
        })

    return payment_details

