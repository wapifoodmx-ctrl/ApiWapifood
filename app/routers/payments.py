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
    PlanType.EMPRESARIAL: "price_1RMCkLAcLh3gfk7AkMlivuYU",
    PlanType.BASICO_IMPRESORA: "price_1RmKjEAcLh3gfk7AErXZJ3I1",
    PlanType.RESTAURANTE_IMPRESORA: "price_1RmKqcAcLh3gfk7ACUUqKfrK",
    PlanType.PLUS_RESTAURANTE_IMPRESORA: "price_1RmKv3AcLh3gfk7A1ZGDGx90"
}

#/ plan basico impresora : price_1RmKjEAcLh3gfk7AErXZJ3I1
#/ plan restaurante impresora : price_1RmKqcAcLh3gfk7ACUUqKfrK
#/ plan plu resturante impresora : price_1RmKv3AcLh3gfk7A1ZGDGx90  

#------------------------------------------
#----------------------------------price_1RMGJPAcLh3gfk7AeZCmoNOs es el id_del precio 



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



#-----------------------------------------------------------------
#-----------------------------------------------------------------


# @router.post("/create-checkout-session")
# async def create_checkout_session(
#     subscription_request: SubscriptionRequest,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         price_id = PLAN_PRICES.get(subscription_request.plan)
#         if not price_id:
#             raise HTTPException(status_code=400, detail="Plan no válido")

#         # Crear un cliente de Stripe si no existe
#         customer = stripe.Customer.create(email=current_user.email)
#         checkout_session = stripe.checkout.Session.create(
#             line_items=[
#                 {"price": price_id, "quantity": 1},
#             ],
#             mode="subscription",
#             customer=customer.id,
#             success_url="https://comandapp.h-dev.xyz/success/?session_id={CHECKOUT_SESSION_ID}",
#             #success_url=YOUR_DOMAIN + "/payments/success?session_id={CHECKOUT_SESSION_ID}",
#             cancel_url="https://comandapp.h-dev.xyz/error",
#             #cancel_url=YOUR_DOMAIN + "/payments/cancel",
#             metadata={"user_id": str(current_user.id_users)},
#         )

#         # Log antes de guardar el registro
#         print(f"Checkout Session creada: ID={checkout_session.id}")
#         print(f"Customer: {checkout_session.customer}")
#         print(f"Subscription: {checkout_session.subscription}")
#         print(f"URL: {checkout_session.url}")

#         payment = Payments(
#             payment_method="pasarela",
#             amount=0,
#             date=datetime.utcnow(),
#             user_id=current_user.id_users,
#             stripe_customer_id=checkout_session.customer,
#             subscription_id=checkout_session.subscription,
#             plan=subscription_request.plan.value,
#             status=PaymentStatus.PENDING,
#             checkout_session_id=checkout_session.id,
#             email=current_user.email, # Guardar el email del usuario
#         )
#         print(f"Registro a guardar: {payment.__dict__}")
#         db.add(payment)
#         try:
#             db.commit()
#             db.refresh(payment)
#             print(f"Pago guardado: ID={payment.id_payments}, Checkout Session ID={payment.checkout_session_id}, Customer ID={payment.stripe_customer_id}, Subscription ID={payment.subscription_id}")
#         except Exception as e:
#             db.rollback()
#             print(f"Error al guardar el pago: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Error al guardar el pago: {str(e)}")

#         return JSONResponse(
#             status_code=200,
#             content={"checkout_url": checkout_session.url}
#         )

#     except stripe.error.StripeError as e:
#         raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")

######################################################################################################
# @router.post("/create-checkout-session")
# async def create_checkout_session(
#     subscription_request: SubscriptionRequest,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         price_id = PLAN_PRICES.get(subscription_request.plan)
#         if not price_id:
#             raise HTTPException(status_code=400, detail="Plan no válido")

#         # Crear un cliente de Stripe si no existe
#         customer = stripe.Customer.create(email=current_user.email)
#         checkout_session = stripe.checkout.Session.create(
#             line_items=[
#                 {"price": price_id, "quantity": 1},
#             ],
#             mode="subscription",
#             customer=customer.id,
#             success_url="https://comandapp.h-dev.xyz/success/?session_id={CHECKOUT_SESSION_ID}",
#             cancel_url="https://comandapp.h-dev.xyz/error",
#             metadata={"user_id": str(current_user.id_users)},
#         )

#         # Log antes de guardar el registro
#         print(f"Sesión de Checkout creada: ID={checkout_session.id}")
#         print(f"Cliente: {checkout_session.customer}")
#         print(f"Suscripción: {checkout_session.subscription}")
#         print(f"URL: {checkout_session.url}")

#         payment = Payments(
#             payment_method="pasarela",
#             amount=0,  # Esto se actualizará con el webhook de Stripe
#             date=datetime.utcnow(),
#             user_id=current_user.id_users,
#             stripe_customer_id=checkout_session.customer,
#             subscription_id=checkout_session.subscription,
#             plan=subscription_request.plan.value,
#             status=PaymentStatus.PENDING,
#             checkout_session_id=checkout_session.id,
#             email=current_user.email,
#         )
#         print(f"Registro a guardar: {payment.__dict__}")
#         db.add(payment)
#         try:
#             db.commit()
#             db.refresh(payment)
#             print(f"Pago guardado: ID={payment.id_payments}, Checkout Session ID={payment.checkout_session_id}, Customer ID={payment.stripe_customer_id}, Subscription ID={payment.subscription_id}")

#             # Validar y crear mesas o detalles de mesas según el plan
#             plan_mesas = {
#                 "basico": 1,
#                 "profesional": 16,
#                 "empresarial": 26
#             }
#             mesas = plan_mesas.get(subscription_request.plan.value, 0)
#             if mesas == 0:
#                 raise HTTPException(status_code=400, detail="Plan no reconocido")

#             # Verificar si ya existen detalles o mesas para evitar duplicados
#             existing_details = db.query(TableDetails).filter(TableDetails.user_id == current_user.id_users).all()
#             existing_tables = db.query(Tables).filter(Tables.user_id == current_user.id_users).all()
#             if existing_details or existing_tables:
#                 raise HTTPException(status_code=400, detail="Las mesas o detalles ya están creados para este usuario")

#             # Crear detalles de mesas (puedes elegir entre create_table_details o generate_tables_sub)
#             table_details = []
#             for i in range(1, mesas + 1):
#                 detail = TableDetails(
#                     user_id=current_user.id_users,
#                     table_number=i,
#                     estado=TablesEnum.Libre,
#                     cantidad_ventas_por_mesa=0.0
#                 )
#                 table_details.append(detail)
#             db.add_all(table_details)
#             db.commit()

#             print(f"Se han creado {mesas} detalles de mesas para el usuario")
#         except Exception as e:
#             db.rollback()
#             print(f"Error al crear detalles de mesas: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Error al crear detalles de mesas: {str(e)}")

#         return JSONResponse(
#             status_code=200,
#             content={"checkout_url": checkout_session.url}
#         )

#     except stripe.error.StripeError as e:
#         raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")
    

# @router.post("/create-checkout-session")
# async def create_checkout_session(
#     subscription_request: SubscriptionRequest,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         price_id = PLAN_PRICES.get(subscription_request.plan)
#         if not price_id:
#             raise HTTPException(status_code=400, detail="Plan no válido")

#         # Verificar si ya existen detalles o mesas ANTES de crear el pago
#         existing_details = db.query(TableDetails).filter(TableDetails.user_id == current_user.id_users).all()
#         existing_tables = db.query(Tables).filter(Tables.user_id == current_user.id_users).all()
        
#         # Crear un cliente de Stripe si no existe
#         customer = stripe.Customer.create(email=current_user.email)
#         checkout_session = stripe.checkout.Session.create(
#             line_items=[
#                 {"price": price_id, "quantity": 1},
#             ],
#             mode="subscription",
#             customer=customer.id,
#             success_url="https://wapifood.com/success/?session_id={CHECKOUT_SESSION_ID}",
#             cancel_url="https://wapifood.com/error",
#             metadata={"user_id": str(current_user.id_users)},
#         )

#         # Log antes de guardar el registro
#         print(f"Sesión de Checkout creada: ID={checkout_session.id}")
#         print(f"Cliente: {checkout_session.customer}")
#         print(f"Suscripción: {checkout_session.subscription}")
#         print(f"URL: {checkout_session.url}")

#         # Asegurarse de usar el valor del enum
#         plan_value = subscription_request.plan.value
#         print(f"Valor del plan a insertar: {plan_value}")

#          # Calcular la fecha de caducidad según el plan
#         current_date = datetime.utcnow()
#         if subscription_request.plan in [PlanType.BASICO_IMPRESORA, PlanType.RESTAURANTE_IMPRESORA, PlanType.PLUS_RESTAURANTE_IMPRESORA]:
#             subscription_end_date = current_date + timedelta(days=365)  # 1 año para planes con impresora
#         else:
#             subscription_end_date = current_date + timedelta(days=30)  # 1 mes para planes mensuales

#         payment = Payments(
#             payment_method="pasarela",
#             amount=0,  # Esto se actualizará con el webhook de Stripe
#             date=datetime.utcnow(),
#             user_id=current_user.id_users,
#             stripe_customer_id=checkout_session.customer,
#             subscription_id=checkout_session.subscription,
#             plan=plan_value,  # Usar el valor del enum explícitamente
#             status=PaymentStatus.PENDING,
#             checkout_session_id=checkout_session.id,
#             email=current_user.email,
#             subscription_end_date=subscription_end_date  # Guardar la fecha de caducidad
#         )
#         print(f"Registro a guardar: {payment.__dict__}")
#         db.add(payment)
        
#         try:
#             db.commit()
#             db.refresh(payment)
#             print(f"Pago guardado: ID={payment.id_payments}, Checkout Session ID={payment.checkout_session_id}, Customer ID={payment.stripe_customer_id}, Subscription ID={payment.subscription_id}")

#             # Solo crear mesas si NO existen previamente
#             if not existing_details and not existing_tables:
#                 # Validar y crear mesas o detalles de mesas según el plan
#                 plan_mesas = {
#                     PlanType.BASICO.value: 1,
#                     PlanType.PROFESIONAL.value: 16,
#                     PlanType.EMPRESARIAL.value: 26,
#                     PlanType.BASICO_IMPRESORA.value: 1,
#                     PlanType.RESTAURANTE_IMPRESORA.value: 16,
#                     PlanType.PLUS_RESTAURANTE_IMPRESORA.value: 26
#                 }
#                 mesas = plan_mesas.get(subscription_request.plan.value, 0)
#                 if mesas == 0:
#                     raise HTTPException(status_code=400, detail="Plan no reconocido")

#                 # Crear detalles de mesas
#                 table_details = []
#                 for i in range(1, mesas + 1):
#                     detail = TableDetails(
#                         user_id=current_user.id_users,
#                         table_number=i,
#                         estado=TablesEnum.Libre,
#                         cantidad_ventas_por_mesa=0.0
#                     )
#                     table_details.append(detail)
#                 db.add_all(table_details)
#                 db.commit()

#                 print(f"Se han creado {mesas} detalles de mesas para el usuario")
#             else:
#                 print(f"Las mesas ya existen para el usuario {current_user.id_users}, omitiendo creación")

#         except Exception as e:
#             db.rollback()
#             print(f"Error al procesar pago y mesas: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Error al procesar pago y mesas: {str(e)}")

#         return JSONResponse(
#             status_code=200,
#             content={"checkout_url": checkout_session.url}
#         )

#     except stripe.error.StripeError as e:
#         raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")


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

        # Crear cliente Stripe
        customer = stripe.Customer.create(email=current_user.email)
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {"price": price_id, "quantity": 1},
            ],
            mode="subscription",
            customer=customer.id,
            success_url="https://wapifood.com/success/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://wapifood.com/error",
            metadata={"user_id": str(current_user.id_users)},
        )

        # Fecha de expiración del plan
        current_date = datetime.utcnow()
        if subscription_request.plan in [
            PlanType.BASICO_IMPRESORA,
            PlanType.RESTAURANTE_IMPRESORA,
            PlanType.PLUS_RESTAURANTE_IMPRESORA
        ]:
            subscription_end_date = current_date + timedelta(days=365)
        else:
            subscription_end_date = current_date + timedelta(days=30)

        # Registro de pago inicial
        plan_value = subscription_request.plan.value
        payment = Payments(
            payment_method="pasarela",
            amount=0,  # Se actualizará en el webhook
            date=datetime.utcnow(),
            user_id=current_user.id_users,
            stripe_customer_id=checkout_session.customer,
            subscription_id=checkout_session.subscription,
            plan=plan_value,
            status=PaymentStatus.PENDING,
            checkout_session_id=checkout_session.id,
            email=current_user.email,
            subscription_end_date=subscription_end_date
        )
        db.add(payment)

        try:
            db.commit()
            db.refresh(payment)
            print(f"Pago guardado correctamente con ID {payment.id_payments}")

        except Exception as e:
            db.rollback()
            print(f"Error al guardar pago: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al guardar pago: {str(e)}")

        return JSONResponse(
            status_code=200,
            content={"checkout_url": checkout_session.url}
        )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Error inesperado: {str(e)}")

#-----------------------------------------------------------------
#-----------------------------------------------------------------
#-------------FUNCION PARA SINCRONIZAR MESAS
#-----------------------------------------------------------------

def sync_tables_with_subscription(db: Session, user_id: int, plan: str, amount: float):
    """
    Sincroniza las mesas (Tables y TableDetails) con el plan de suscripción activo.
    Elimina mesas sobrantes y crea nuevas si es necesario.
    """
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

    # Mapear el monto al valor correcto del enum SubscriptionAmount
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
        subscription_amount = subscription_amount_enum.value  # Obtener el valor numérico del enum
        print(f"Subscription amount mapped to: {subscription_amount}")  # Depuración
    except (ValueError, TypeError) as e:
        print(f"Error al mapear monto a SubscriptionAmount: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Monto {amount} no válido para SubscriptionAmount")

    try:
        # Mesas actuales en TableDetails
        mesas_actuales_details = db.query(TableDetails).filter(TableDetails.user_id == user_id).order_by(TableDetails.table_number).all()
        total_actuales_details = len(mesas_actuales_details)

        # Mesas actuales en Tables
        mesas_actuales_tables = db.query(TablesModel).filter(TablesModel.user_id == user_id).order_by(TablesModel.number).all()
        total_actuales_tables = len(mesas_actuales_tables)

        # Eliminar mesas sobrantes en TableDetails
        if total_actuales_details > mesas_permitidas:
            mesas_a_eliminar = mesas_actuales_details[mesas_permitidas:]
            for mesa in mesas_a_eliminar:
                db.delete(mesa)
            print(f"Se eliminaron {len(mesas_a_eliminar)} mesas sobrantes en TableDetails.")

        # Eliminar mesas sobrantes en Tables
        if total_actuales_tables > mesas_permitidas:
            mesas_a_eliminar = mesas_actuales_tables[mesas_permitidas:]
            for mesa in mesas_a_eliminar:
                db.delete(mesa)
            print(f"Se eliminaron {len(mesas_a_eliminar)} mesas sobrantes en Tables.")

        # Crear mesas faltantes en TableDetails
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

        # Crear mesas faltantes en Tables
        if total_actuales_tables < mesas_permitidas:
            nuevas_mesas = []
            for i in range(total_actuales_tables + 1, mesas_permitidas + 1):
                nuevas_mesas.append(
                    TablesModel(
                        number=i,
                        capacity=4,
                        state=TablesEnum.Libre,
                        user_id=user_id,
                        subscription_amount=subscription_amount  # Usar el valor numérico
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

#-----------------------------------------------------------------
#-----------------------------------------------------------------


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
    
##----------------------------------------------------------------------------
#-----------------------------------------------------------------------------



# @router.post("/webhook", status_code=status.HTTP_200_OK)
# async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
#     payload = await request.body()
#     sig_header = request.headers.get("stripe-signature")

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, stripe_webhook_secret)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail="Carga inválida")
#     except stripe.error.SignatureVerificationError as e:
#         raise HTTPException(status_code=400, detail="Firma inválida")

#     try:
#         if event["type"] == "checkout.session.completed":
#             checkout_session = event["data"]["object"]
#             subscription_id = checkout_session.get("subscription")
#             print(f"Procesando checkout.session.completed - Session ID: {checkout_session.id}, Subscription ID: {subscription_id}")

#             if not subscription_id:
#                 print("No subscription_id in event")
#                 return {"status": "ignored", "message": "No subscription_id in event"}

#             payment = db.query(Payments).filter(Payments.checkout_session_id == checkout_session.id).first()
#             if not payment:
#                 print(f"Pago no encontrado para checkout_session_id: {checkout_session.id}")
#                 return {"status": "ignored", "message": "Payment not found"}

#             user = db.query(User).filter(User.id_users == payment.user_id).first()
#             if not user:
#                 print(f"Usuario no encontrado para user_id: {payment.user_id}")
#                 return {"status": "ignored", "message": "User not found"}

#             payment.subscription_id = subscription_id or payment.subscription_id
#             payment.stripe_customer_id = checkout_session.customer or payment.stripe_customer_id

#             try:
#                 subscription = stripe.Subscription.retrieve(subscription_id)
#                 print(f"Subscription retrieved: {subscription}")
#             except stripe.error.InvalidRequestError as e:
#                 print(f"Error al recuperar la suscripción: {str(e)}")
#                 return {"status": "error", "message": f"Error al recuperar la suscripción: {str(e)}"}

#             try:
#                 if subscription.plan and subscription.plan.amount:
#                     amount = subscription.plan.amount / 100
#                 else:
#                     price_id = subscription.plan.id if subscription.plan else None
#                     if price_id:
#                         price = stripe.Price.retrieve(price_id)
#                         amount = price.unit_amount / 100
#                     else:
#                         amount = 0
#                 payment.amount = amount
#                 print(f"Amount set to: {amount}")
#             except stripe.error.InvalidRequestError as e:
#                 print(f"Error al recuperar el precio: {str(e)}")
#                 amount = 0
#                 payment.amount = amount

#             # Manejo aún más robusto de current_period_end
#             subscription_end_date = None
#             try:
#                 # Verificar primero si el atributo existe y es accesible
#                 current_period_end = getattr(subscription, 'current_period_end', None)
#                 print(f"Valor de current_period_end: {current_period_end}")
#                 if current_period_end is not None and isinstance(current_period_end, (int, float)) and current_period_end > 0:
#                     subscription_end_date = datetime.utcfromtimestamp(current_period_end)
#                     print(f"Subscription end date from current_period_end: {subscription_end_date}")
#                 else:
#                     print(f"current_period_end no válido o ausente: {current_period_end}")
#                     raise ValueError("current_period_end no disponible o inválido")
#             except (ValueError, TypeError, OSError) as e:
#                 print(f"Error al procesar current_period_end: {str(e)}")
#                 try:
#                     # Verificar current_period_start de manera similar
#                     current_period_start = getattr(subscription, 'current_period_start', None)
#                     plan_interval = subscription.plan.interval if subscription.plan and hasattr(subscription.plan, 'interval') else None
#                     print(f"current_period_start: {current_period_start}, plan.interval: {plan_interval}")
#                     if current_period_start is not None and isinstance(current_period_start, (int, float)) and current_period_start > 0 and plan_interval:
#                         start_date = datetime.utcfromtimestamp(current_period_start)
#                         if plan_interval == "month":
#                             subscription_end_date = start_date + timedelta(days=30)
#                         elif plan_interval == "year":
#                             subscription_end_date = start_date + timedelta(days=365)
#                         else:
#                             subscription_end_date = start_date + timedelta(days=30)
#                         print(f"Subscription end date calculated from start: {subscription_end_date}")
#                     else:
#                         print(f"current_period_start o plan.interval no disponibles: start={current_period_start}, interval={plan_interval}")
#                         subscription_end_date = datetime.utcnow() + timedelta(days=30)
#                         print(f"Subscription end date calculated manually: {subscription_end_date}")
#                 except (ValueError, TypeError, OSError) as e:
#                     print(f"Error al calcular la fecha de finalización: {str(e)}")
#                     subscription_end_date = datetime.utcnow() + timedelta(days=30)
#                     print(f"Usando fecha por defecto: {subscription_end_date}")

#             payment.subscription_end_date = subscription_end_date
#             payment.status = PaymentStatus.COMPLETED
#             payment.email = user.email
#             try:
#                 db.commit()
#                 db.refresh(payment)
#                 print(f"Pago actualizado en la base de datos: {payment.__dict__}")
#             except Exception as e:
#                 db.rollback()
#                 print(f"Error al actualizar la base de datos: {str(e)}")
#                 raise HTTPException(status_code=500, detail=f"Error al actualizar la base de datos: {str(e)}")

#         elif event["type"] == "customer.subscription.updated":
#             subscription = event["data"]["object"]
#             subscription_id = subscription.get("id")

#             payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
#             if not payment:
#                 return {"status": "ignored", "message": "Payment not found"}

#             user = db.query(User).filter(User.id_users == payment.user_id).first()
#             if not user:
#                 return {"status": "ignored", "message": "User not found"}

#             # Actualizar el monto si cambió el plan
#             if subscription.plan and subscription.plan.amount:
#                 amount = subscription.plan.amount / 100
#                 payment.amount = amount
#                 print(f"Updated amount to: {amount}")

#             # Actualizar la fecha de finalización
#             if subscription.current_period_end:
#                 subscription_end_date = datetime.utcfromtimestamp(subscription.current_period_end)
#                 payment.subscription_end_date = subscription_end_date
#                 print(f"Updated subscription end date to: {subscription_end_date}")
#             else:
#                 if subscription.current_period_start and subscription.plan and subscription.plan.interval:
#                     start_date = datetime.utcfromtimestamp(subscription.current_period_start)
#                     if subscription.plan.interval == "month":
#                         subscription_end_date = start_date + timedelta(days=30)
#                     elif subscription.plan.interval == "year":
#                         subscription_end_date = start_date + timedelta(days=365)
#                     else:
#                         subscription_end_date = start_date + timedelta(days=30)
#                     payment.subscription_end_date = subscription_end_date
#                     print(f"Calculated subscription end date: {subscription_end_date}")
#                 else:
#                     payment.subscription_end_date = datetime.utcnow() + timedelta(days=30)
#                     print(f"Manually set subscription end date: {payment.subscription_end_date}")

#             # Actualizar el estado si es necesario (por ejemplo, si se reactiva)
#             if subscription.status == "active" or subscription.status == "trialing":
#                 payment.status = PaymentStatus.COMPLETED
#             elif subscription.status == "canceled":
#                 payment.status = PaymentStatus.FAILED
#             payment.email = user.email
#             db.commit()
#             db.refresh(payment)
#             print(f"Payment updated in DB: {payment.__dict__}")

#         elif event["type"] == "customer.subscription.deleted":
#             subscription = event["data"]["object"]
#             subscription_id = subscription.get("id")

#             payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
#             if not payment:
#                 return {"status": "ignored", "message": "Payment not found"}

#             user = db.query(User).filter(User.id_users == payment.user_id).first()
#             if user:
#                 payment.email = user.email

#             payment.status = PaymentStatus.FAILED
#             payment.subscription_end_date = None  # Limpia la fecha de finalización
#             db.commit()
#             db.refresh(payment)
#             print(f"Payment canceled in DB: {payment.__dict__}")

#         elif event["type"] == "payment_intent.succeeded":
#             payment_intent = event["data"]["object"]
#             subscription_id = payment_intent.get("metadata", {}).get("subscription_id")
#             if not subscription_id:
#                 if payment_intent.get("charges", {}).get("data"):
#                     charge = payment_intent["charges"]["data"][0]
#                     invoice_id = charge.get("invoice")
#                     if invoice_id:
#                         invoice = stripe.Invoice.retrieve(invoice_id)
#                         subscription_id = invoice.get("subscription")

#             if not subscription_id:
#                 return {"status": "ignored", "message": "No subscription_id in payment_intent"}

#             payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
#             if not payment:
#                 return {"status": "ignored", "message": "Payment not found"}

#             user = db.query(User).filter(User.id_users == payment.user_id).first()
#             if user:
#                 payment.email = user.email

#             payment.stripe_payment_intent_id = payment_intent["id"]
#             db.commit()
#             db.refresh(payment)

#         else:
#             return {"status": "ignored", "message": f"Event type {event['type']} not handled"}

#         return {"status": "success"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error al procesar el evento: {str(e)}")

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, stripe_webhook_secret)
    except ValueError as e:
        print(f"Error: Carga inválida - {str(e)}")
        raise HTTPException(status_code=400, detail="Carga inválida")
    except stripe.error.SignatureVerificationError as e:
        print(f"Error: Firma inválida - {str(e)}")
        raise HTTPException(status_code=400, detail="Firma inválida")

    try:
        if event["type"] == "checkout.session.completed":
            checkout_session = event["data"]["object"]
            subscription_id = checkout_session.get("subscription")
            print(f"Procesando checkout.session.completed - Session ID: {checkout_session.id}, Subscription ID: {subscription_id}")

            if not subscription_id:
                print("No subscription_id in event")
                return {"status": "ignored", "message": "No subscription_id in event"}

            payment = db.query(Payments).filter(Payments.checkout_session_id == checkout_session.id).first()
            if not payment:
                print(f"Pago no encontrado para checkout_session_id: {checkout_session.id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                print(f"Usuario no encontrado para user_id: {payment.user_id}")
                return {"status": "ignored", "message": "User not found"}

            payment.subscription_id = subscription_id or payment.subscription_id
            payment.stripe_customer_id = checkout_session.customer or payment.stripe_customer_id

            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                print(f"Subscription retrieved: {subscription}")
            except stripe.error.InvalidRequestError as e:
                print(f"Error al recuperar la suscripción: {str(e)}")
                return {"status": "error", "message": f"Error al recuperar la suscripción: {str(e)}"}

            # Calcular monto
            amount = 0
            try:
                if subscription.plan and subscription.plan.amount is not None:
                    amount = subscription.plan.amount / 100
                else:
                    price_id = subscription.plan.id if subscription.plan else None
                    if price_id:
                        price = stripe.Price.retrieve(price_id)
                        amount = price.unit_amount / 100
                payment.amount = amount
                print(f"Amount set to: {amount}")
            except Exception as e:
                print(f"Error al obtener el monto: {str(e)}")
                payment.amount = amount

            # Calcular subscription_end_date
            subscription_end_date = None
            try:
                # Acceder a current_period_end desde el objeto subscription
                current_period_end = getattr(subscription, "current_period_end", None)
                print(f"current_period_end: {current_period_end}")
                if current_period_end is not None and isinstance(current_period_end, (int, float)) and current_period_end > 0:
                    subscription_end_date = datetime.utcfromtimestamp(current_period_end)
                    print(f"subscription_end_date from current_period_end: {subscription_end_date}")
                else:
                    raise ValueError("current_period_end no válido o ausente")
            except (ValueError, TypeError, AttributeError, OSError) as e:
                print(f"Error al procesar current_period_end: {str(e)}")
                try:
                    current_period_start = getattr(subscription, "current_period_start", None)
                    plan_interval = getattr(subscription.plan, "interval", None) if subscription.plan else None
                    print(f"current_period_start: {current_period_start}, plan.interval: {plan_interval}")
                    if current_period_start is not None and isinstance(current_period_start, (int, float)) and current_period_start > 0 and plan_interval:
                        start_date = datetime.utcfromtimestamp(current_period_start)
                        days_to_add = 365 if plan_interval == "year" or amount > 300 else 30
                        subscription_end_date = start_date + timedelta(days=days_to_add)
                        print(f"subscription_end_date calculated from start: {subscription_end_date}")
                    else:
                        raise ValueError("current_period_start o plan.interval no válido")
                except (ValueError, TypeError, AttributeError, OSError) as e:
                    print(f"Error al calcular subscription_end_date: {str(e)}")
                    days_to_add = 365 if amount > 300 else 30
                    subscription_end_date = datetime.utcnow() + timedelta(days=days_to_add)
                    print(f"subscription_end_date set to default: {subscription_end_date}")

            payment.subscription_end_date = subscription_end_date
            payment.status = PaymentStatus.COMPLETED
            payment.email = user.email
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.__dict__}")

            # Sincronizar mesas
            sync_tables_with_subscription(db, payment.user_id, payment.plan, payment.amount)

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")
            print(f"Procesando customer.subscription.updated - Subscription ID: {subscription_id}")

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                print(f"Pago no encontrado para subscription_id: {subscription_id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if not user:
                print(f"Usuario no encontrado para user_id: {payment.user_id}")
                return {"status": "ignored", "message": "User not found"}

            # Actualizar monto y plan
            amount = 0
            try:
                if subscription.plan and subscription.plan.amount is not None:
                    amount = subscription.plan.amount / 100
                else:
                    price_id = subscription.plan.id if subscription.plan else None
                    if price_id:
                        price = stripe.Price.retrieve(price_id)
                        amount = price.unit_amount / 100
                payment.amount = amount
                print(f"Updated amount to: {amount}")
            except Exception as e:
                print(f"Error al obtener el monto: {str(e)}")
                payment.amount = amount

            # Actualizar plan
            price_id = subscription.plan.id if subscription.plan else None
            plan = None
            for plan_type, pid in PLAN_PRICES.items():
                if pid == price_id:
                    plan = plan_type
                    break
            if plan:
                payment.plan = plan
                print(f"Updated plan to: {plan}")
            else:
                print(f"Price ID {price_id} no encontrado en PLAN_PRICES")
                return {"status": "ignored", "message": "Plan not recognized"}

            # Actualizar subscription_end_date
            subscription_end_date = None
            try:
                current_period_end = getattr(subscription, "current_period_end", None)
                print(f"current_period_end: {current_period_end}")
                if current_period_end is not None and isinstance(current_period_end, (int, float)) and current_period_end > 0:
                    subscription_end_date = datetime.utcfromtimestamp(current_period_end)
                    print(f"subscription_end_date from current_period_end: {subscription_end_date}")
                else:
                    raise ValueError("current_period_end no válido o ausente")
            except (ValueError, TypeError, OSError) as e:
                print(f"Error al procesar current_period_end: {str(e)}")
                try:
                    current_period_start = getattr(subscription, "current_period_start", None)
                    plan_interval = getattr(subscription.plan, "interval", None) if subscription.plan else None
                    print(f"current_period_start: {current_period_start}, plan.interval: {plan_interval}")
                    if current_period_start is not None and isinstance(current_period_start, (int, float)) and current_period_start > 0 and plan_interval:
                        start_date = datetime.utcfromtimestamp(current_period_start)
                        days_to_add = 365 if plan_interval == "year" or amount > 300 else 30
                        subscription_end_date = start_date + timedelta(days=days_to_add)
                        print(f"subscription_end_date calculated from start: {subscription_end_date}")
                    else:
                        raise ValueError("current_period_start o plan.interval no válido")
                except (ValueError, TypeError, OSError) as e:
                    print(f"Error al calcular subscription_end_date: {str(e)}")
                    days_to_add = 365 if amount > 300 else 30
                    subscription_end_date = datetime.utcnow() + timedelta(days=days_to_add)
                    print(f"subscription_end_date set to default: {subscription_end_date}")

            payment.subscription_end_date = subscription_end_date
            payment.status = PaymentStatus.COMPLETED if subscription.status in ["active", "trialing"] else PaymentStatus.FAILED
            payment.email = user.email
            db.commit()
            db.refresh(payment)
            print(f"Pago actualizado: {payment.__dict__}")

            # Sincronizar mesas
            sync_tables_with_subscription(db, payment.user_id, payment.plan, payment.amount)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")
            print(f"Procesando customer.subscription.deleted - Subscription ID: {subscription_id}")

            payment = db.query(Payments).filter(Payments.subscription_id == subscription_id).first()
            if not payment:
                print(f"Pago no encontrado para subscription_id: {subscription_id}")
                return {"status": "ignored", "message": "Payment not found"}

            user = db.query(User).filter(User.id_users == payment.user_id).first()
            if user:
                payment.email = user.email

            payment.status = PaymentStatus.FAILED
            payment.subscription_end_date = None
            db.commit()
            db.refresh(payment)
            print(f"Pago cancelado: {payment.__dict__}")

            # Eliminar todas las mesas
            db.query(TablesModel).filter(TablesModel.user_id == payment.user_id).delete()
            db.query(TableDetails).filter(TableDetails.user_id == payment.user_id).delete()
            db.commit()
            print(f"Se eliminaron todas las mesas para el usuario {payment.user_id}")

        else:
            print(f"Evento no manejado: {event['type']}")
            return {"status": "ignored", "message": f"Event type {event['type']} not handled"}

        return {"status": "success"}

    except Exception as e:
        print(f"Error al procesar webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el evento: {str(e)}")
    
#-----------------------------------------------------------------
#-----------------------------------------------------------------

    
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


@router.get("/check-payment")
async def check_payment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Usar el correo del usuario autenticado
    user_email = current_user.email
    print(f"Buscando pagos para el correo: {user_email}")

    # Definir el límite de 30 días
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    print(f"Fecha límite para los pagos: {cutoff_date}")

    # Fecha actual para verificar suscripciones activas
    current_time = datetime.utcnow()
    print(f"Fecha actual: {current_time}")

    # Buscar la última suscripción activa
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

