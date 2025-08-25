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
from app.schemas import SubscriptionRequest, PaymentResponse
from typing import List
from app.enums import TablesEnum
from app.db.models import Tables as TablesModel, TableDetails, Payments
from app.enums import TablesEnum, SubscriptionAmount, PaymentMethodEnum
from decimal import Decimal
import mercadopago

load_dotenv()
# stripe.api_key = os.getenv("STRIPE_API_KEY")
# stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# if not stripe.api_key:
#     raise ValueError("No se encontró la clave de API de Stripe en las variables de entorno")


# Configura Mercado Pago
# Configurar Mercado Pago SDK
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
MERCADO_PAGO_PUBLIC_KEY = os.getenv("MERCADO_PAGO_PUBLIC_KEY")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "https://api.wapifood.com").rstrip("/")
#YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "http://127.0.0.1:8000")
#mercado_pago_webhook_secret = os.getenv("MERCADO_PAGO_WEBHOOK_SECRET")

if not MERCADO_PAGO_ACCESS_TOKEN:
      raise ValueError("MERCADO_PAGO_ACCESS_TOKEN no está configurado")
if not MERCADO_PAGO_PUBLIC_KEY:
      raise ValueError("MERCADO_PAGO_PUBLIC_KEY no está configurado")



router = APIRouter(
    prefix="/payments",
    tags=["payments"]
)

#YOUR_DOMAIN = "http://127.0.0.1:8000"

# PLAN_PRICES = {
#     PlanType.BASICO: "price_1RMGJPAcLh3gfk7AeZCmoNOs" ,        #"prod_SGk7H4kqVBUvtP", # Reemplaza con el ID real del precio de Stripe
#     PlanType.PROFESIONAL: "price_1RMCjmAcLh3gfk7A4QwwMBLW",
#     PlanType.EMPRESARIAL: "price_1RMCkLAcLh3gfk7AkMlivuYU",
#     PlanType.BASICO_IMPRESORA: "price_1RmKjEAcLh3gfk7AErXZJ3I1",
#     PlanType.RESTAURANTE_IMPRESORA: "price_1RmKqcAcLh3gfk7ACUUqKfrK",
#     PlanType.PLUS_RESTAURANTE_IMPRESORA: "price_1RmKv3AcLh3gfk7A1ZGDGx90"
# }


#/ plan basico impresora : price_1RmKjEAcLh3gfk7AErXZJ3I1
#/ plan restaurante impresora : price_1RmKqcAcLh3gfk7ACUUqKfrK
#/ plan plu resturante impresora : price_1RmKv3AcLh3gfk7A1ZGDGx90  

#------------------------------------------
#----------------------------------price_1RMGJPAcLh3gfk7AeZCmoNOs es el id_del precio 
# Crear planes de suscripción al iniciar la aplicación

# Crear planes de suscripción al iniciar la aplicación

mercado_pago_sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)

# Mapa de precios para los planes
PLAN_PRICES = {
    PlanType.INAUGURACION: {
        "amount": 15.0,
        "currency": "MXN",
        "description": "Plan de Inauguración (Promocional)"
    },
    PlanType.BASICO: {
        "amount": 100.0,
        "currency": "MXN",
        "description": "Plan Básico"
    },
    PlanType.PROFESIONAL: {
        "amount": 200.0,
        "currency": "MXN",
        "description": "Plan Profesional"
    },
    PlanType.EMPRESARIAL: {
        "amount": 300.0,
        "currency": "MXN",
        "description": "Plan Empresarial"
    },
    PlanType.BASICO_IMPRESORA: {
        "amount": 1960.0,
        "currency": "MXN",
        "description": "Plan Básico con Impresora"
    },
    PlanType.RESTAURANTE_IMPRESORA: {
        "amount": 2920.0,
        "currency": "MXN",
        "description": "Plan Restaurante con Impresora"
    },
    PlanType.PLUS_RESTAURANTE_IMPRESORA: {
        "amount": 3880.0,
        "currency": "MXN",
        "description": "Plan Plus Restaurante con Impresora"
    }
}



@router.post("/create-checkout-session")
async def create_checkout_session(
    subscription_request: SubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        plan_details = PLAN_PRICES.get(subscription_request.plan)
        if not plan_details:
            raise HTTPException(status_code=400, detail="Plan no válido")
        

    # Validar que el plan de inauguración solo esté disponible para usuarios nuevos
        if subscription_request.plan == PlanType.INAUGURACION:
            existing_payment = db.query(Payments).filter(
                Payments.user_id == current_user.id_users,
                Payments.status == PaymentStatus.COMPLETED
            ).first()
            if existing_payment:
                raise HTTPException(status_code=400, detail="El plan de inauguración solo está disponible para usuarios nuevos")

        # Crear preferencia de pago único
        preference_data = {
            "items": [
                {
                    "title": plan_details["description"],
                    "quantity": 1,
                    "unit_price": float(plan_details["amount"]),
                    "currency_id": "MXN"
                }
            ],
            "payer": {
                "email": current_user.email
            },
            "back_urls": {
                "success": "https://wapifood.com/success",
                "failure": "https://wapifood.com/error"
            
            },
            "auto_return": "approved",
            "external_reference": f"user_{current_user.id_users}",
            "payment_methods": {
                "installments": 1
            },
            "notification_url": f"https://api.wapifood.com/payments/webhook"  # Agregar el webhook
        }

        preference_response = mercado_pago_sdk.preference().create(preference_data)
        print(f"Respuesta de creación de preferencia: {preference_response['response']}")
        preference = preference_response["response"]
        preference_id = preference.get("id")
        if not preference_id:
            raise ValueError("No se encontró 'id' en la respuesta de creación de preferencia")

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
            amount=Decimal(plan_details["amount"]),
            date=datetime.utcnow(),
            subscription_end_date=subscription_end_date,
            user_id=current_user.id_users,
            mercado_pago_preference_id=preference_id,  # Usar un campo específico para preference_id
            plan=subscription_request.plan.value,
            status=PaymentStatus.PENDING,
            email=current_user.email,
            checkout_url=preference.get("init_point")
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        print(f"Pago guardado: ID={payment.id_payments}, Preference ID={payment.mercado_pago_preference_id}, URL={payment.checkout_url}")

        return JSONResponse(
            status_code=200,
            content={
                "checkout_url": preference.get("init_point"),
                "payment_id": payment.id_payments,
                "message": "Enlace de pago generado con éxito"
            }
        )

    except Exception as e:
        print(f"Error al crear pago: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al crear pago: {str(e)}")
    

# Configuración de Mercado Pago (ya definida en tu código)

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        # Log para depuración
        print(f"Webhook Headers: {dict(request.headers)}")
        print(f"Webhook Query Params: {dict(request.query_params)}")
        body = await request.body()
        print(f"Webhook recibido - Cuerpo crudo: {body}")

        # Obtener parámetros de consulta
        query_params = request.query_params
        topic = query_params.get("topic") or query_params.get("type")
        payment_id = query_params.get("id") or query_params.get("data.id")
        
        # Intentar obtener cuerpo JSON
        try:
            payload = await request.json()
            topic = topic or payload.get("topic") or payload.get("type") or payload.get("action")
            payment_id = payment_id or payload.get("data", {}).get("id") or payload.get("resource", "").split("/")[-1]
            print(f"Webhook JSON Payload: {payload}")
        except ValueError:
            print("No se recibió un cuerpo JSON válido")

        if not topic:
            print("No se encontró topic en el evento")
            return {"status": "ignored", "message": "No topic in event"}

        if topic in ["payment", "payment.created"]:
            if not payment_id:
                print("No se encontró payment_id en el evento")
                return {"status": "ignored", "message": "No payment_id in event"}

            # Obtener información del pago
            payment_response = mercado_pago_sdk.payment().get(payment_id)
            print(f"Respuesta de obtención de pago: {payment_response['response']}")
            payment_data = payment_response["response"]

            # Intentar obtener preference_id
            preference_id = payment_data.get("preference_id")
            if not preference_id:
                merchant_order_id = payment_data.get("order", {}).get("id")
                if merchant_order_id:
                    merchant_order_response = mercado_pago_sdk.merchant_order().get(merchant_order_id)
                    print(f"Respuesta de merchant_order: {merchant_order_response['response']}")
                    merchant_order_data = merchant_order_response["response"]
                    preference_id = merchant_order_data.get("preference_id")
                    print(f"Preference ID desde merchant_order: {preference_id}")

            if not preference_id:
                print("No se encontró preference_id en el pago o merchant_order")
                return {"status": "ignored", "message": "No preference_id in payment or merchant_order"}

            payment = db.query(Payments).filter(Payments.mercado_pago_preference_id == preference_id).first()
            if not payment:
                print(f"Pago no encontrado para preference_id: {preference_id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                print(f"Usuario no encontrado para user_id: {payment.user_id}")
                return {"status": "ignored", "message": "User not found"}

            payment.mercado_pago_payment_id = payment_id
            payment.amount = Decimal(payment_data.get("transaction_amount", payment.amount))
            payment_status = payment_data.get("status")
            if payment_status == "approved":
                payment.status = PaymentStatus.COMPLETED
            elif payment_status in ["rejected", "cancelled"]:
                payment.status = PaymentStatus.FAILED
            else:
                payment.status = PaymentStatus.PENDING
            print(f"Actualizando estado del pago a: {payment.status}")
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
            print("Base de datos actualizada correctamente")
            db.refresh(payment)
            print(f"Pago actualizado: {payment.__dict__}")

            sync_tables_with_subscription(db, payment.user_id, payment.plan.value, float(payment.amount))

        elif topic == "merchant_order":
            merchant_order_id = payment_id or query_params.get("id") or payload.get("resource", "").split("/")[-1]
            print(f"Merchant Order ID: {merchant_order_id}")
            if not merchant_order_id:
                print("No se encontró merchant_order_id en el evento")
                return {"status": "ignored", "message": "No merchant_order_id in event"}

            merchant_order_response = mercado_pago_sdk.merchant_order().get(merchant_order_id)
            print(f"Respuesta de merchant_order: {merchant_order_response['response']}")
            merchant_order_data = merchant_order_response["response"]
            preference_id = merchant_order_data.get("preference_id")
            print(f"Preference ID desde merchant_order: {preference_id}")

            if not preference_id:
                print("No se encontró preference_id en el merchant_order")
                return {"status": "ignored", "message": "No preference_id in merchant_order"}

            payment = db.query(Payments).filter(Payments.mercado_pago_preference_id == preference_id).first()
            if not payment:
                print(f"Pago no encontrado para preference_id: {preference_id}")
                return {"status": "ignored", "message": "Payment not found"}

            payments = merchant_order_data.get("payments", [])
            for payment_data in payments:
                payment_id = payment_data.get("id")
                payment_status = payment_data.get("status")
                payment.mercado_pago_payment_id = payment_id
                if payment_status == "approved":
                    payment.status = PaymentStatus.COMPLETED
                elif payment_status in ["rejected", "cancelled"]:
                    payment.status = PaymentStatus.FAILED
                else:
                    payment.status = PaymentStatus.PENDING
                print(f"Actualizando estado del pago a: {payment.status}")

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
                print("Base de datos actualizada correctamente")
                db.refresh(payment)
                print(f"Pago actualizado: {payment.__dict__}")

                sync_tables_with_subscription(db, payment.user_id, payment.plan.value, float(payment.amount))

        else:
            print(f"Evento no manejado: {topic}")
            return {"status": "ignored", "message": f"Event topic {topic} not handled"}

        return {"status": "success"}

    except Exception as e:
        print(f"Error al procesar webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el evento: {str(e)}")
    

@router.get("/success", status_code=status.HTTP_200_OK)
async def payment_success(request: Request, db: Session = Depends(get_db)):
    preference_id = request.query_params.get("preference_id")
    payment_id = request.query_params.get("payment_id")
    print(f"Procesando /success - Preference ID: {preference_id}, Payment ID: {payment_id}")

    if not preference_id or not payment_id:
        print("Faltan parámetros preference_id o payment_id")
        raise HTTPException(status_code=400, detail="Falta el ID de la preferencia o del pago")

    payment = db.query(Payments).filter(Payments.mercado_pago_preference_id == preference_id).first()
    if not payment:
        print(f"Pago no encontrado para preference_id: {preference_id}")
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    user = db.query(User).filter(User.id_users == payment.user_id).first()
    if not user:
        print(f"Usuario no encontrado para user_id: {payment.user_id}")
        raise HTTPException(status_code=404, detail="Usuario asociado al pago no encontrado")

    try:
        payment_response = mercado_pago_sdk.payment().get(payment_id)
        payment_data = payment_response["response"]
        print(f"Estado del pago en /success: {payment_data.get('status')}")

        if payment_data.get("status") == "approved":
            payment.status = PaymentStatus.COMPLETED
            payment.mercado_pago_payment_id = payment_id
            if payment_data.get("date_approved"):
                start_date = datetime.strptime(payment_data["date_approved"], "%Y-%m-%dT%H:%M:%S.%f%z")
                days_to_add = 365 if payment.plan in [
                    PlanType.BASICO_IMPRESORA,
                    PlanType.RESTAURANTE_IMPRESORA,
                    PlanType.PLUS_RESTAURANTE_IMPRESORA
                ] else 30
                payment.subscription_end_date = start_date + timedelta(days=days_to_add)
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.__dict__}")
            sync_tables_with_subscription(db, payment.user_id, payment.plan.value, float(payment.amount))
        else:
            print(f"Estado del pago no es approved: {payment_data.get('status')}")
            raise HTTPException(status_code=400, detail=f"El pago no está aprobado: {payment_data.get('status')}")

    except Exception as e:
        print(f"Error al verificar pago: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al verificar pago: {str(e)}")

    subscription_end_date = payment.subscription_end_date.isoformat() if payment.subscription_end_date else None
    return {
        "message": "¡Pago procesado con éxito!",
        "status": payment.status.value,
        "user_email": user.email,
        "subscription_end_date": subscription_end_date
    }


@router.get("/cancel", status_code=status.HTTP_200_OK)
async def payment_cancel():
    return {"message": "Pago cancelado."}

@router.get("/check-payment")
async def check_payment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_email = current_user.email
    print(f"Buscando pagos para el correo: {user_email}")

    cutoff_date = datetime.utcnow() - timedelta(days=365)
    current_time = datetime.utcnow()

    payment = db.query(Payments).filter(
        Payments.email == user_email,
        Payments.date >= cutoff_date,
        #Payments.status.in_([PaymentStatus.COMPLETED, PaymentStatus.PENDING]),
        Payments.status == PaymentStatus.COMPLETED,
        Payments.subscription_end_date != None,
        Payments.subscription_end_date > current_time
    ).order_by(Payments.date.desc()).first()

    # Obtener la hora de ejecución en formato ISO
    execution_time = datetime.utcnow().isoformat()


    if not payment:
        print("No se encontraron pagos activos")
        return {
            "message": "No se encontraron pagos activos en los últimos 30 días",
            "has_active_subscription": False
        }

    print(f"Pago activo encontrado: ID {payment.id_payments}, Fecha: {payment.date}, Plan: {payment.plan}")

    return {
        "message": "Último pago activo encontrado",
        "has_active_subscription": True,
        "payment": {
            "id": payment.id_payments,
            "amount": float(payment.amount),
            "date": payment.date.isoformat(),
            "plan": payment.plan,
            "status": payment.status.value,
            "subscription_end_date": payment.subscription_end_date.isoformat() if payment.subscription_end_date else None,
            "checkout_url": payment.checkout_url
        },
        "execution_time": execution_time  # Agregar hora de ejecución
    }

@router.get("/me", status_code=status.HTTP_200_OK, response_model=List[PaymentResponse])
async def get_user_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payments = db.query(Payments).filter(Payments.user_id == current_user.id_users).all()
    
    if not payments:
        raise HTTPException(status_code=404, detail="No se encontraron pagos para este usuario")

    return payments

def sync_tables_with_subscription(db: Session, user_id: int, plan: str, amount: float):
    plan_mesas = {
        PlanType.INAUGURACION.value: 1,  # 1 mesa para el plan de inauguración
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
        15.0: SubscriptionAmount.PLAN_INAUGURACION,
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
    except (ValueError, TypeError) as e:
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

@router.get("/public-key")
async def get_mercado_pago_public_key():
    return {"public_key": MERCADO_PAGO_PUBLIC_KEY}



@router.get("/verify-payment/{payment_id}")
async def verify_payment(payment_id: str, db: Session = Depends(get_db)):
    try:
        payment_response = mercado_pago_sdk.payment().get(payment_id)
        payment_data = payment_response["response"]
        print(f"Estado del pago {payment_id}: {payment_data.get('status')}")

        preference_id = payment_data.get("preference_id")
        payment = db.query(Payments).filter(Payments.mercado_pago_preference_id == preference_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        payment.mercado_pago_payment_id = payment_id
        payment_status = payment_data.get("status")
        if payment_status == "approved":
            payment.status = PaymentStatus.COMPLETED
        elif payment_status in ["rejected", "cancelled"]:
            payment.status = PaymentStatus.FAILED
        else:
            payment.status = PaymentStatus.PENDING
        db.commit()
        db.refresh(payment)
        return {"message": "Pago verificado", "status": payment.status.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar pago: {str(e)}")