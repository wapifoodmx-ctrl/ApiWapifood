from fastapi import APIRouter, Depends, HTTPException, status, Form
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import select, update, func
from typing import List
import logging
from uuid import uuid4, UUID
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User, Payments
from app.schemas import Orders as OrdersSchema, OrdersResponse, OrdersCreate, OrderCreateResponse, OrderFinalizeResponse, OrdersDetails, OrderDetailsByUUIDResponse, OrderDetailItem
from app.enums import RoleOrders, TablesEnum, OrderStatusEnum, PlanType, PaymentStatus, SubscriptionAmount, PaymentMethodEnum
from app.db.models import OrdersDetails as OrdersDetailsModel
from app.db.models import Payments as PaymentsModel, UserConfirmationCode
from app.repository.auth import get_current_user
from decimal import Decimal
from datetime import datetime,  timedelta
import random

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

# Esquema OAuth2 para el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

# @router.get("/", response_model=List[OrdersSchema], status_code=status.HTTP_200_OK)
# def obtener_ordenes(db: Session = Depends(get_db), current_user = Depends(oauth2_scheme)):
#     get_current_user(current_user, db)
#     """Obtiene todas las órdenes de la base de datos del usuario."""
#     Orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).all()
#     return Orders

#------------------------------------------
#------------------------------------------



# @router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED,
#     description="Crea una nueva orden con detalles para múltiples productos existentes y asigna una mesa disponible."
# )
# async def crear_orden(
#     product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
#     quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     token: str = Depends(oauth2_scheme)
# ):
#     """
#     Crea una nueva orden con detalles para múltiples productos existentes y asigna una mesa disponible.
#     Los product_ids y quantities deben ser cadenas separadas por comas.
#     """
#     # 1. Parsear las listas de product_ids y quantities
#     try:
#         product_ids_list = [int(pid) for pid in product_ids.split(",")]
#         quantities_list = [int(qty) for qty in quantities.split(",")]
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Los product_ids y quantities deben ser listas de números enteros separados por comas")

#     # 2. Validar que las listas tengan la misma longitud
#     if len(product_ids_list) != len(quantities_list):
#         raise HTTPException(status_code=400, detail="El número de product_ids y quantities debe ser igual")
#     if not product_ids_list:
#         raise HTTPException(status_code=400, detail="Debe proporcionar al menos un producto")

#     # 3. Validar las cantidades
#     for qty in quantities_list:
#         if qty <= 0:
#             raise HTTPException(status_code=400, detail="Todas las cantidades deben ser mayores que 0")

#     # 4. Verificar que los productos existan y pertenezcan al usuario autenticado
#     products = []
#     total_order = 0.0
#     product_names = []
#     for product_id in product_ids_list:
#         db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
#         if not db_product:
#             raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")
#         if db_product.owner_id != current_user.id_users:
#             raise HTTPException(status_code=403, detail=f"No tienes permiso para crear una orden para el producto con ID {product_id}")
#         products.append(db_product)
#         product_names.append(db_product.name)

#     # 5. Buscar la primera mesa disponible (Libre, number != 1)
#     available_table = db.query(TablesModel).filter(
#         TablesModel.user_id == current_user.id_users,
#         TablesModel.state == TablesEnum.Libre,
#         TablesModel.number != 1  # Excluir la mesa 1 (punto de venta)
#     ).order_by(TablesModel.number.asc()).first()

#     if not available_table:
#         raise HTTPException(status_code=400, detail="No hay mesas disponibles para asignar (todas están ocupadas o no tienes mesas asignadas)")

#     # 6. Calcular el total de la orden
#     for db_product, qty in zip(products, quantities_list):
#         total_order += float(db_product.price) * qty

#     # 7. Crear la orden (Orders) asociada al usuario autenticado
#     db_order = OrdersModel(
#         state=RoleOrders.Ocupado,
#         date_time=datetime.utcnow(),
#         total=total_order,
#         orderscol="Orden creada manualmente",
#         user_id=current_user.id_users,
#         product_name=", ".join(product_names),
#         mesa_id=available_table.id_tables  # Asignar la mesa encontrada
#     )
#     db.add(db_order)

#     # 8. Actualizar el estado de la mesa a Ocupado
#     available_table.state = TablesEnum.Ocupado
#     db.commit()
#     db.refresh(db_order)
#     db.refresh(available_table)

#     # 9. Crear los detalles de pedido (OrdersDetails) para cada producto
#     for db_product, qty in zip(products, quantities_list):
#         unit_price = float(db_product.price)
#         subtotal = qty * unit_price

#         db_order_detail = OrdersDetailsModel(
#             order_id=db_order.id_orders,
#             product_id=db_product.id_products,
#             quantity=qty,
#             unit_price=unit_price,
#             subtotal=subtotal
#         )
#         db.add(db_order_detail)

#     db.commit()

#     # 10. Refrescar la orden para incluir los detalles y el número de la mesa
#     db.refresh(db_order)

#     # Crear una instancia del esquema manualmente para incluir mesa_number
#     order_response = OrderCreateResponse.from_orm(db_order)
#     order_response.mesa_id = db_order.mesa_id  # Asegurar que mesa_id se incluya
#     order_response.mesa_number = available_table.number  # Añadir el número de la mesa

#     return order_response


# @router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED,
#     description="Crea una nueva orden con detalles para múltiples productos existentes y asigna una mesa especificada. La mesa con ID 1 siempre permanece en estado Libre."
# )
# async def crear_orden(
#     product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
#     quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
#     mesa_id: int = Form(..., description="ID de la mesa a asignar a la orden (la mesa con ID 1 siempre permanece disponible)"),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     token: str = Depends(oauth2_scheme)
# ):
#     """
#     Crea una nueva orden con detalles para múltiples productos existentes y asigna una mesa especificada.
#     Los product_ids y quantities deben ser cadenas separadas por comas.
#     La mesa con ID 1 siempre permanece en estado Libre, incluso al asignarse a una orden.
#     """
#     # 1. Parsear las listas de product_ids y quantities
#     try:
#         product_ids_list = [int(pid) for pid in product_ids.split(",")]
#         quantities_list = [int(qty) for qty in quantities.split(",")]
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Los product_ids y quantities deben ser listas de números enteros separados por comas")

#     # 2. Validar que las listas tengan la misma longitud
#     if len(product_ids_list) != len(quantities_list):
#         raise HTTPException(status_code=400, detail="El número de product_ids y quantities debe ser igual")
#     if not product_ids_list:
#         raise HTTPException(status_code=400, detail="Debe proporcionar al menos un producto")

#     # 3. Validar las cantidades
#     for qty in quantities_list:
#         if qty <= 0:
#             raise HTTPException(status_code=400, detail="Todas las cantidades deben ser mayores que 0")

#     # 4. Verificar que la mesa exista y pertenezca al usuario autenticado
#     db_table = db.query(TablesModel).filter(
#         TablesModel.id_tables == mesa_id,
#         TablesModel.user_id == current_user.id_users
#     ).first()
#     if not db_table:
#         raise HTTPException(status_code=404, detail=f"Mesa con ID {mesa_id} no encontrada o no te pertenece")
    
#     # 5. Generar UUID para la orden
#     if db_table.state == TablesEnum.Ocupado and mesa_id != 1:  # Solo verificar órdenes previas si no es la mesa 1
#         # Obtener el UUID de la orden más reciente para esta mesa
#         latest_order = db.query(OrdersModel).filter(
#             OrdersModel.mesa_id == mesa_id,
#             OrdersModel.state == RoleOrders.Ocupado
#         ).order_by(OrdersModel.date_time.desc()).first()
#         order_uuid = latest_order.order_uuid if latest_order else str(uuid.uuid4())
#     else:
#         order_uuid = str(uuid.uuid4())  # Nuevo UUID si la mesa está libre o es la mesa 1

#     # 6. Verificar que los productos existan y pertenezcan al usuario autenticado
#     products = []
#     total_order = 0.0
#     product_names = []
#     for product_id in product_ids_list:
#         db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
#         if not db_product:
#             raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")
#         if db_product.owner_id != current_user.id_users:
#             raise HTTPException(status_code=403, detail=f"No tienes permiso para crear una orden para el producto con ID {product_id}")
#         products.append(db_product)
#         product_names.append(db_product.name)

#     # 7. Calcular el total de la orden
#     for db_product, qty in zip(products, quantities_list):
#         total_order += float(db_product.price) * qty

#     # 8. Crear la orden (Orders) asociada al usuario autenticado
#     db_order = OrdersModel(
#         mesa_id=mesa_id,
#         state=RoleOrders.Ocupado,
#         order_status=OrderStatusEnum.Pendiente,  # Estado inicial del pedido
#         date_time=datetime.utcnow(),
#         total=total_order,
#         orderscol="Orden creada manualmente",
#         user_id=current_user.id_users,
#         product_name=", ".join(product_names),
#         order_uuid=order_uuid  # Usar el UUID generado o mantenido
#     )
#     db.add(db_order)

#     # 9. Actualizar el estado de la mesa a Ocupado solo si no es la mesa 1
#     if db_table.state == TablesEnum.Libre and mesa_id != 1:
#         db_table.state = TablesEnum.Ocupado
#     db.commit()
#     db.refresh(db_order)
#     db.refresh(db_table)

#     # 10. Crear los detalles de pedido (OrdersDetails) para cada producto
#     for db_product, qty in zip(products, quantities_list):
#         unit_price = float(db_product.price)
#         subtotal = qty * unit_price

#         db_order_detail = OrdersDetailsModel(
#             order_id=db_order.id_orders,
#             product_id=db_product.id_products,
#             quantity=qty,
#             unit_price=unit_price,
#             subtotal=subtotal
#         )
#         db.add(db_order_detail)

#     db.commit()

#     # 11. Refrescar la orden para incluir los detalles y el número de la mesa
#     db.refresh(db_order)

#     # Crear una instancia del esquema manualmente para incluir mesa_number
#     order_response = OrderCreateResponse.from_orm(db_order)
#     order_response.mesa_id = db_order.mesa_id
#     order_response.mesa_number = db_table.number
#     order_response.order_uuid = db_order.order_uuid  # Incluir el UUID en la respuesta

#     return order_response

#--------------------------------------------
#------------------------------------------




#------------------------------------------
#------------------------------------------

@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED,
    description="Crea una nueva orden o añade productos a una orden existente para una mesa especificada. La mesa con número 1 siempre permanece en estado Libre y sus órdenes inician como PuntoDeVenta. El order_uuid es opcional; si no se proporciona o se envía vacío, se genera uno único. Para pedidos adicionales de la misma mesa, usa el mismo UUID solo si la orden está activa (no finalizada ni cancelada).")
async def crear_orden(
    product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
    quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
    table_number: int = Form(..., description="Número de la mesa a asignar a la orden (la mesa con número 1 siempre permanece disponible)"),
    metodo_pago: PaymentMethodEnum = Form(PaymentMethodEnum.efectivo, description="Método de pago de la orden (efectivo, tarjeta, pasarela)"),
    order_uuid: str = Form(None, description="UUID opcional para identificar la orden; si no se proporciona o se envía vacío, se genera uno único. Para pedidos adicionales de la misma mesa, usa el mismo UUID solo si la orden está activa."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    logging.basicConfig(level=logging.DEBUG)

    # 1. Parsear las listas de product_ids y quantities
    try:
        product_ids_list = [int(pid) for pid in product_ids.split(",")]
        quantities_list = [int(qty) for qty in quantities.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Los product_ids y quantities deben ser listas de números enteros separados por comas")

    # 2. Validar que las listas tengan la misma longitud
    if len(product_ids_list) != len(quantities_list):
        raise HTTPException(status_code=400, detail="El número de product_ids y quantities debe ser igual")
    if not product_ids_list:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un producto")

    # 3. Validar las cantidades
    for qty in quantities_list:
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Todas las cantidades deben ser mayores que 0")

    # 4. Validar la suscripción activa
    payment = db.query(Payments).filter(
        Payments.user_id == current_user.id_users,
        Payments.status == PaymentStatus.COMPLETED,
        Payments.subscription_end_date >= datetime.now()
    ).order_by(Payments.date.desc()).first()
    if not payment:
        raise HTTPException(status_code=403, detail="No tienes una suscripción activa")

    logging.debug(f"payment.amount: {payment.amount}, type: {type(payment.amount)}")

    # 5. Determinar el número máximo de mesas según el monto de la suscripción
    subscription_mesas = {
        SubscriptionAmount.PLAN_100.value: 1,
        SubscriptionAmount.PLAN_200.value: 16,
        SubscriptionAmount.PLAN_300.value: 26
    }
    try:
        amount_float = float(payment.amount) if payment.amount else 0.0
    except (TypeError, ValueError) as e:
        logging.error(f"Error convirtiendo payment.amount: {payment.amount}, error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al procesar el monto de la suscripción")
    max_mesas = subscription_mesas.get(amount_float, 0)
    logging.debug(f"amount_float: {amount_float}, max_mesas: {max_mesas}")
    if max_mesas == 0:
        raise HTTPException(status_code=400, detail=f"Monto de suscripción no reconocido: {amount_float}")
    if table_number < 1 or table_number > max_mesas:
        raise HTTPException(status_code=400, detail=f"El número de mesa debe estar entre 1 y {max_mesas}")

    # 6. Verificar que la mesa exista y pertenezca al usuario autenticado
    db_table = db.query(TablesModel).filter(
        TablesModel.number == table_number,
        TablesModel.user_id == current_user.id_users
    ).first()
    if not db_table:
        raise HTTPException(status_code=404, detail=f"Mesa con número {table_number} no encontrada o no te pertenece")

    # 7. Determinar el order_uuid y manejar órdenes existentes
    existing_order = None
    if order_uuid:
        try:
            UUID(order_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="El order_uuid proporcionado no es válido")
        existing_orders = db.query(OrdersModel).filter(
            OrdersModel.order_uuid == order_uuid,
            OrdersModel.user_id == current_user.id_users
        ).all()
        for order in existing_orders:
            if order.order_status in [OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado]:
                raise HTTPException(
                    status_code=400,
                    detail=f"El order_uuid {order_uuid} corresponde a una orden finalizada o cancelada y no puede ser reutilizado"
                )
            if order.mesa_id != db_table.id_tables:
                raise HTTPException(status_code=400, detail="El order_uuid proporcionado ya está en uso para otra mesa")
            if order.order_status not in [OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado]:
                existing_order = order  # Encontramos una orden activa

    if not order_uuid or order_uuid == "":
        if db_table.state == TablesEnum.Ocupado and table_number != 1:
            latest_order = db.query(OrdersModel).filter(
                OrdersModel.mesa_id == db_table.id_tables,
                OrdersModel.order_status.notin_([OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado])
            ).order_by(OrdersModel.date_time.desc()).first()
            if latest_order:
                order_uuid = latest_order.order_uuid
                existing_order = latest_order
            else:
                order_uuid = str(uuid4())
        else:
            order_uuid = str(uuid4())

    # 8. Verificar que los productos existan y pertenezcan al usuario autenticado
    products = []
    total_order = 0.0
    product_names = []
    for product_id in product_ids_list:
        db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
        if not db_product:
            raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")
        if db_product.owner_id != current_user.id_users:
            raise HTTPException(status_code=403, detail=f"No tienes permiso para crear una orden para el producto con ID {product_id}")
        products.append(db_product)
        product_names.append(db_product.name)

    # 9. Calcular el total de los nuevos productos
    new_total = 0.0
    for db_product, qty in zip(products, quantities_list):
        new_total += float(db_product.price) * qty

    # 10. Si existe una orden activa, actualizarla; si no, crear una nueva
    if existing_order:
        # Actualizar la orden existente
        existing_order.total = float(existing_order.total or 0.0) + new_total
        existing_order.product_name = ", ".join(
            list(set(existing_order.product_name.split(", ") + product_names)) if existing_order.product_name else product_names
        )
        existing_order.date_time = datetime.now()  # Actualizar la fecha
        existing_order.metodo_pago = metodo_pago  # Actualizar método de pago
        # Actualizar el estado de la orden según las mini órdenes
        mini_orders = existing_order.order_details
        if all(detail.order_detail_status == OrderStatusEnum.Finalizado for detail in mini_orders):
            existing_order.order_status = OrderStatusEnum.Finalizado
        elif any(detail.order_detail_status == OrderStatusEnum.Cancelado for detail in mini_orders):
            existing_order.order_status = OrderStatusEnum.Cancelado
        else:
            existing_order.order_status = OrderStatusEnum.Pendiente  # Estado por defecto si hay mezcla
        db.add(existing_order)

        # Añadir nuevos detalles con estatus Pendiente
        for db_product, qty in zip(products, quantities_list):
            unit_price = float(db_product.price)
            subtotal = qty * unit_price
            db_order_detail = OrdersDetailsModel(
                order_id=existing_order.id_orders,
                product_id=db_product.id_products,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
                order_detail_status=OrderStatusEnum.Pendiente
            )
            db.add(db_order_detail)
    else:
        # Crear una nueva orden
        initial_status = OrderStatusEnum.PuntoDeVenta if table_number == 1 else OrderStatusEnum.Pendiente
        db_order = OrdersModel(
            mesa_id=db_table.id_tables,
            state=RoleOrders.Ocupado if table_number != 1 else RoleOrders.Libre,  # Mesa 1 siempre Libre
            order_status=initial_status,  # PuntoDeVenta para mesa 1
            date_time=datetime.now(),
            total=new_total,
            orderscol="Orden creada manualmente",
            product_name=", ".join(product_names),
            user_id=current_user.id_users,
            order_uuid=order_uuid,
            metodo_pago=metodo_pago
            # No se incluye codigo_confirmacion, se usa el server_default
        )
        db.add(db_order)

        # Actualizar el estado de la mesa solo si no es la mesa 1
        if db_table.number != 1 and db_table.state == TablesEnum.Libre:
            db_table.state = TablesEnum.Ocupado

        db.commit()
        db.refresh(db_order)

        # Crear los detalles de pedido con estatus Pendiente
        for db_product, qty in zip(products, quantities_list):
            unit_price = float(db_product.price)
            subtotal = qty * unit_price
            db_order_detail = OrdersDetailsModel(
                order_id=db_order.id_orders,
                product_id=db_product.id_products,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
                order_detail_status=OrderStatusEnum.Pendiente
            )
            db.add(db_order_detail)

    db.commit()
    db.refresh(db_table)

    # 11. Refrescar la orden para la respuesta y actualizar estado final
    db_order = existing_order or db_order
    db.refresh(db_order)

    # 10. Crear respuesta con el número de mesa
    order_response = OrderCreateResponse.from_orm(db_order)
    order_response.mesa_id = db_order.mesa_id
    order_response.mesa_number = db_table.number
    order_response.order_uuid = db_order.order_uuid

    return order_response
#------------------------------------------
#------------------------------------------

@router.get("/orders", response_model=List[OrdersResponse], status_code=status.HTTP_200_OK)
def obtenemos_orders_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las órdenes del usuario autenticado, incluyendo sus detalles."""
    orders = (
        db.query(OrdersModel)
        .filter(OrdersModel.user_id == current_user.id_users)
        .options(joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product))
        .all()
    )
    
    if not orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

    orders_dicts = []
    for order in orders:
        mesa_number = None
        if order.mesa_id:
            mesa = db.query(TablesModel).filter(TablesModel.id_tables == order.mesa_id).first()
            if mesa:
                mesa_number = mesa.number

    # Convertir los objetos OrdersModel a diccionarios
    orders_dicts = []
    for order in orders:
        order_dict = {
            "id_orders": order.id_orders,
            # "mesa_id": order.mesa_id,
            "mesa_number": mesa_number,
            "state": order.state,
            "order_status": order.order_status,  # Agregado
            "date_time": order.date_time,
            "total": float(order.total) if order.total is not None else 0.0,
            "orderscol": order.orderscol,  # Requerido por el esquema
            "user_id": order.user_id,  # Requerido por el esquema
            "order_uuid": order.order_uuid,  # Requerido por el esquema
            "product_name": order.product_name or "Sin nombre",
            "ticket_number": order.ticket_number if order.ticket_number else "Sin número de ticket",
            "details": [
                {
                    #"id_orders_details": detail.id_orders_details,
                    #"order_id": detail.order_id,
                    #"product_id": detail.product_id,
                    "quantity": detail.quantity,
                    "unit_price": detail.unit_price if detail.unit_price is not None else 0.0,  # Valor por defecto
                    "subtotal": detail.subtotal if detail.subtotal is not None else 0.0, # Valor por defecto
                    "order_detail_status": detail.order_detail_status  # Agregado para el estatus del detalle
                }
                for detail in order.order_details
            ]
        }
        orders_dicts.append(order_dict)

    return [OrdersResponse.model_validate(order_dict) for order_dict in orders_dicts]

#------------------------------------------
#------------------------------------------

@router.get("/final/{order_uuid}", response_model=List[dict], status_code=status.HTTP_200_OK)
def obtener_ordenes_por_uuid(
    order_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Obtener todas las órdenes asociadas al UUID proporcionado para este usuario
    ordenes = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).all()
    
    
    if not ordenes:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este UUID")
    
    
    # Calcular la orden final (suma de totals, por ejemplo)
    ordenes_dict = []
    total_final = 0.0
    for orden in ordenes:
        orden_dict = {
            "id_orders": orden.id_orders,
            "mesa_id": orden.mesa_id,
            #"mesa_number": mesa_number,
            "state": orden.state,
            "date_time": orden.date_time,
            "total": float(orden.total) if orden.total else 0.0,
            "product_name": orden.product_name,
            "ticke_number": orden.ticket_number if orden.ticket_number else "Sin número de ticket"
        }
        ordenes_dict.append(orden_dict)
        total_final += float(orden.total) if orden.total else 0.0

        
    
    return [{"ordenes": ordenes_dict, "total_final": total_final}]









#------------------------------------------
#------------------------------------------

@router.get("/summary", response_model=dict, status_code=status.HTTP_200_OK)
def dame_resumen_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene un resumen de las órdenes del usuario autenticado (Total, Pendientes, En Proceso, Completados)."""
    # Total de órdenes
    total_orders = db.query(OrdersModel).filter(OrdersModel.user_id == current_user.id_users).count()

    # Contar órdenes por estado
    pending = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.state == "Pendiente"
    ).count()
    in_process = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.state == "En Proceso"
    ).count()
    completed = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.state == "Completado"
    ).count()

    # Retornar el resumen
    return {
        "Total de Pedidos": total_orders,
        "Pendientes": pending,
        "En Proceso": in_process,
        "Completados": completed
    }



#------------------------------------------
#-------------------------------------------------------------------





#------------------------------------------
#------------------------------------------

# @router.put("/orders/{order_uuid}/cambio_estatus", response_model=OrderFinalizeResponse, status_code=status.HTTP_200_OK)
# async def finalizar_orden(
#     order_uuid: str,
#     order_status: OrderStatusEnum,
#     metodo_pago: PaymentMethodEnum,  # Nuevo parámetro para cambiar el método de pago
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     # Obtener todas las órdenes con el order_uuid para el usuario
#     db_orders = db.query(OrdersModel).filter(
#         OrdersModel.order_uuid == order_uuid,
#         OrdersModel.user_id == current_user.id_users
#     ).all()

#     if not db_orders:
#         raise HTTPException(status_code=404, detail=f"No se encontraron órdenes con UUID {order_uuid} o no te pertenecen")

#     # Verificar que todas las órdenes tengan una mesa asociada
#     mesa_ids = {order.mesa_id for order in db_orders if order.mesa_id}
#     if not mesa_ids:
#         raise HTTPException(status_code=400, detail="Las órdenes no están asociadas a ninguna mesa")
#     if len(mesa_ids) > 1:
#         raise HTTPException(status_code=400, detail="Las órdenes están asociadas a múltiples mesas, lo cual no es permitido")

#     mesa_id = mesa_ids.pop()
#     db_table = db.query(TablesModel).filter(TablesModel.id_tables == mesa_id).first()
#     if not db_table:
#         raise HTTPException(status_code=400, detail="La mesa no existe")

#     # Verificar si alguna orden ya está finalizada o cancelada
#     for order in db_orders:
#         if order.order_status in (OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado):
#             raise HTTPException(status_code=400, detail=f"La orden con ID {order.id_orders} ya ha sido finalizada o cancelada")

#     # Actualizar el estado y el método de pago de todas las órdenes
#     for order in db_orders:
#         order.order_status = order_status
#         order.metodo_pago = metodo_pago  # Actualizar el método de pago
#         db.add(order)

#         # Si la orden se finaliza, actualizar todos los detalles a Finalizado
#         if order_status == OrderStatusEnum.Finalizado:
#             order_details = db.query(OrdersDetailsModel).filter(
#                 OrdersDetailsModel.order_id == order.id_orders
#             ).all()
#             for detail in order_details:
#                 if detail.order_detail_status != OrderStatusEnum.Finalizado or detail.order_detail_status != OrderStatusEnum.Cancelado:
#                     detail.order_detail_status = OrderStatusEnum.Finalizado
#                     db.add(detail)
        
#         # Si la orden se canela, cancela todo los detalles
#         if order_status == OrderStatusEnum.Cancelado:
#             order_details = db.query(OrdersDetailsModel).filter(
#                 OrdersDetailsModel.order_id == order.id_orders
#             ).all()
#             for detail in order_details:
#                 detail.order_detail_status = OrderStatusEnum.Cancelado
#                 db.add(detail)

    

#     # Liberar la mesa si el estado es Finalizado y no es la mesa número 1
#     if order_status == OrderStatusEnum.Finalizado and db_table.number != 1:
#         db_table.state = TablesEnum.NoDisponible

#     db.commit()

#     # Refrescar la primera orden y la mesa para la respuesta
#     db.refresh(db_orders[0])
#     db.refresh(db_table)

#     return OrderFinalizeResponse(
#         message=f"Cambio de estado y método de pago de {len(db_orders)} orden(es) realizado con éxito",
#         order_id=db_orders[0].id_orders,  # Usar la primera orden para la respuesta
#         mesa_id=mesa_id,
#         order_status=order_status,
#         mesa_state=db_table.state
#     )

@router.put("/orders/{order_uuid}/cambio_estatus", response_model=OrderFinalizeResponse, status_code=status.HTTP_200_OK)
async def finalizar_orden(
    order_uuid: str,
    order_status: OrderStatusEnum,
    metodo_pago: PaymentMethodEnum,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Obtener todas las órdenes con el order_uuid para el usuario
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).all()

    if not db_orders:
        raise HTTPException(status_code=404, detail=f"No se encontraron órdenes con UUID {order_uuid} o no te pertenecen")

    # Verificar que todas las órdenes tengan una mesa asociada
    mesa_ids = {order.mesa_id for order in db_orders if order.mesa_id}
    if not mesa_ids:
        raise HTTPException(status_code=400, detail="Las órdenes no están asociadas a ninguna mesa")
    if len(mesa_ids) > 1:
        raise HTTPException(status_code=400, detail="Las órdenes están asociadas a múltiples mesas, lo cual no es permitido")

    mesa_id = mesa_ids.pop()
    db_table = db.query(TablesModel).filter(TablesModel.id_tables == mesa_id).first()
    if not db_table:
        raise HTTPException(status_code=400, detail="La mesa no existe")

    # Verificar si alguna orden ya está finalizada o cancelada
    for order in db_orders:
        if order.order_status in (OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado):
            raise HTTPException(status_code=400, detail=f"La orden con ID {order.id_orders} ya ha sido finalizada o cancelada")

    # 🆕 Obtener el siguiente número de ticket solo si el estado es "Finalizado"
    ticket_number = None
    if order_status == OrderStatusEnum.Finalizado:
        # Verificar si alguna orden ya tiene un ticket_number asignado
        existing_ticket = None
        for order in db_orders:
            if order.ticket_number is not None:
                existing_ticket = order.ticket_number
                break
        
        if existing_ticket:
            # Usar el ticket existente
            ticket_number = existing_ticket
        else:
            # Obtener el último ticket_number del usuario
            last_ticket = db.query(OrdersModel).filter(
                OrdersModel.user_id == current_user.id_users,
                OrdersModel.ticket_number.is_not(None)
            ).order_by(OrdersModel.ticket_number.desc()).first()
            
            # Calcular el siguiente número de ticket
            if last_ticket and last_ticket.ticket_number:
                ticket_number = int(last_ticket.ticket_number) + 1
            else:
                ticket_number = 1  # Primer ticket para este usuario
                
    # Actualizar el estado y el método de pago de todas las órdenes
    for order in db_orders:
        order.order_status = order_status
        order.metodo_pago = metodo_pago

        # 🆕 Asignar el número de ticket solo si la orden se finaliza
        if order_status == OrderStatusEnum.Finalizado:
            order.ticket_number = ticket_number

        db.add(order)

        # Si la orden se finaliza, actualizar todos los detalles a Finalizado
        if order_status == OrderStatusEnum.Finalizado:
            order_details = db.query(OrdersDetailsModel).filter(
                OrdersDetailsModel.order_id == order.id_orders
            ).all()
            for detail in order_details:
                if detail.order_detail_status not in (OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado):
                    detail.order_detail_status = OrderStatusEnum.Finalizado
                    db.add(detail)
        
        # Si la orden se cancela, cancela todos los detalles y establece todos los precios en 0 
        if order_status == OrderStatusEnum.Cancelado:
            order_details = db.query(OrdersDetailsModel).filter(
                OrdersDetailsModel.order_id == order.id_orders
            ).all()
            for detail in order_details:
                detail.order_detail_status = OrderStatusEnum.Cancelado
                detail.unit_price = 0.0  # Establecer el precio unitario a 0
                detail.subtotal = 0.0
                detail.quantity = 0  # Establecer la cantidad a 0
                db.add(detail)

    # Liberar la mesa si el estado es Finalizado y no es la mesa número 1
    if order_status == OrderStatusEnum.Finalizado and db_table.number != 1:
        db_table.state = TablesEnum.NoDisponible

    db.commit()

    # Refrescar la primera orden y la mesa para la respuesta
    db.refresh(db_orders[0])
    db.refresh(db_table)

    return OrderFinalizeResponse(
        message=f"Cambio de estado y método de pago de {len(db_orders)} orden(es) realizado con éxito",
        order_id=db_orders[0].id_orders,
        mesa_id=mesa_id,
        order_status=order_status,
        mesa_state=db_table.state,
        ticket_number=ticket_number
        #codigo_confirmacion=db_orders[0].codigo_confirmacion
    )

##--------------------------------------------
#------------------------------------------




#------------------------------------------
#------------------------------------------

@router.get("/{order_uuid}", response_model=OrderDetailsByUUIDResponse, status_code=status.HTTP_200_OK,
    description="Obtiene los detalles de una orden específica por su UUID, incluyendo el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago.")
async def obtener_orden_por_uuid(
    order_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene los detalles de una orden específica por su UUID.
    Retorna el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago.
    """
    # Obtener la orden con el order_uuid para el usuario autenticado
    db_order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),  # Usar el modelo SQLAlchemy OrdersDetails
        joinedload(OrdersModel.user).joinedload(User.user_info)
    ).first()

    if not db_order:
        raise HTTPException(status_code=404, detail=f"Orden con UUID {order_uuid} no encontrada")

    # Construir la lista de detalles de productos
    product_details = [
        OrderDetailItem(
            id_orders_details=detail.id_orders_details,  # Agregar el id_orders_details
            product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
            quantity=detail.quantity,
            unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
            subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
            order_detail_status=detail.order_detail_status
        )
        for detail in db_order.order_details
    ]

    # Obtener el nombre del restaurante desde UserInfo
    restaurant_name = (
        db_order.user.user_info.nombre_restaurante
        if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
        else "Sin nombre de restaurante"
    )

    # Obtener el numero de mesa
    mesa_number = (
        db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
    )

    # Construir la respuesta
    response = OrderDetailsByUUIDResponse(
        id_orders=db_order.id_orders,
        mesa_number=db_order.mesa_id,  
        restaurant_name=restaurant_name,
        order_uuid=db_order.order_uuid,
        date_time=db_order.date_time,
        state=db_order.state,
        order_status=db_order.order_status,
        products=product_details,
        total=float(db_order.total) if db_order.total is not None else 0.0,
        metodo_pago=db_order.metodo_pago,
        ticket_number=db_order.ticket_number  # Incluir el ticket_number si está disponible
    )

    return response
#------------------------------------------
#------------------------------------------


@router.get("/orders/allorders", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene todas las órdenes del usuario autenticado, incluyendo el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago.")
async def dame_todas_las_ordenes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Retorna una lista con el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago para cada orden.
    """
    # Obtener todas las órdenes del usuario autenticado
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),  # Corregido a OrdersDetails
        joinedload(OrdersModel.user).joinedload(User.user_info)
    ).all()

    if not db_orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        # Construir la lista de detalles de productos
        product_details = [
            OrderDetailItem(
                id_orders_details=detail.id_orders_details,  # Agregar id_orders_details
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status  # Agregado para incluir el estado del detalle
            )
            for detail in db_order.order_details
        ]

        # Obtener el nombre del restaurante desde UserInfo
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el numero de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
        )

        # Construir la respuesta
        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Incluir el ticket_number si está disponible
        )
        responses.append(response)

    return responses



#------------------------------------------
#------------------------------------------

@router.get("orders/by-status", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene todas las órdenes del usuario autenticado filtradas por estado, incluyendo el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago.")
async def dame_ordenes_por_estado(
    status: OrderStatusEnum = None,  # Parámetro opcional para filtrar por estado
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Retorna una lista con el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago para cada orden.
    """
    # Obtener todas las órdenes del usuario autenticado
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),  # Corregido a OrdersDetails
        joinedload(OrdersModel.user).joinedload(User.user_info)
    ).all()

    if not db_orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        product_details = [
            OrderDetailItem(
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status,
                id_orders_details=detail.id_orders_details  # Agregar id_orders_details
            )
            for detail in db_order.order_details
        ]

        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )
        # Obtener el numero de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
        )

        # Construir la respuesta
        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Incluir el ticket_number si está disponible
        )
        responses.append(response)

    return responses



#------------------------------------------
#------------------------------------------

# @router.put("/orders/{order_uuid}/cambio_detalles_subordenes", response_model=OrderDetailItem, status_code=status.HTTP_200_OK)
# async def finalizar_orden(
#     order_uuid: str,
#     id_orders_details: int,
#     order_detail_status: OrderStatusEnum,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     # 1. Buscar la orden por UUID y usuario
#     db_order = db.query(OrdersModel).filter(
#         OrdersModel.order_uuid == order_uuid,
#         OrdersModel.user_id == current_user.id_users
#     ).first()

#     if not db_order:
#         raise HTTPException(status_code=404, detail=f"No se encontró una orden con UUID {order_uuid} o no te pertenece")

#     # 2. Buscar el detalle de la orden por id_orders_details y que pertenezca a la orden encontrada
#     db_order_detail = db.query(OrdersDetailsModel).filter(
#         OrdersDetailsModel.id_orders_details == id_orders_details,
#         OrdersDetailsModel.order_id == db_order.id_orders
#     ).first()
#     if not db_order_detail:
#         raise HTTPException(status_code=404, detail=f"No se encontró el detalle con id {id_orders_details} para el UUID {order_uuid}")

#     # Solo permitir modificar si el estado actual NO es Finalizado ni Cancelado
#     if db_order_detail.order_detail_status in [OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado]:
#         raise HTTPException(
#             status_code=400,
#             detail=f"No se puede modificar el estado porque el detalle ya está en estado '{db_order_detail.order_detail_status.value}'"
#         )
    
#     # 3. Cambiar el estado del detalle
#     db_order_detail.order_detail_status = order_detail_status
#     db.add(db_order_detail)
#     db.commit()
#     db.refresh(db_order_detail)


#     # Refrescar la primera orden y la mesa para la respuesta
#     # db.refresh(db_orders[0])
#     # db.refresh(db_table)

#     return OrderDetailItem(
#         product_name=db_order_detail.product.name if db_order_detail.product and db_order_detail.product.name else "Producto desconocido",
#         quantity=db_order_detail.quantity,
#         unit_price=float(db_order_detail.unit_price) if db_order_detail.unit_price is not None else 0.0,
#         subtotal=float(db_order_detail.subtotal) if db_order_detail.subtotal is not None else 0.0,
#         order_detail_status=db_order_detail.order_detail_status
#     )


@router.put("/orders/{order_uuid}/cambio_details_status", response_model=List[OrderDetailItem], status_code=status.HTTP_200_OK)
async def finalizar_orden(
    order_uuid: str,
    id_orders_details: str = Form(...),  # Cadena de IDs separados por comas
    order_detail_status: OrderStatusEnum = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Convertir la cadena de IDs en una lista de enteros
    try:
        id_orders_details_list = [int(id_str) for id_str in id_orders_details.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="El campo id_orders_details debe contener IDs enteros separados por comas (ej. '357,358,359')"
        )

    # 1. Buscar la orden por UUID y usuario
    db_order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).first()

    if not db_order:
        raise HTTPException(status_code=404, detail=f"No se encontró una orden con UUID {order_uuid} o no te pertenece")

    # 2. Buscar los detalles de la orden para los id_orders_details proporcionados
    db_order_details = db.query(OrdersDetailsModel).filter(
        OrdersDetailsModel.id_orders_details.in_(id_orders_details_list),
        OrdersDetailsModel.order_id == db_order.id_orders
    ).all()

    # Verificar que se encontraron todos los detalles solicitados
    if len(db_order_details) != len(id_orders_details_list):
        found_ids = {detail.id_orders_details for detail in db_order_details}
        missing_ids = [id_detail for id_detail in id_orders_details_list if id_detail not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron los detalles con IDs {missing_ids} para el UUID {order_uuid}"
        )

    # 3. Verificar que ningún detalle esté en estado Finalizado o Cancelado
    for detail in db_order_details:
        if detail.order_detail_status in [OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado]:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede modificar el estado porque el detalle con ID {detail.id_orders_details} ya está en estado '{detail.order_detail_status.value}'"
            )

    # 4. Cambiar el estado de los detalles seleccionados y actualizar subtotal
    updated_details = []
    for detail in db_order_details:
        detail.order_detail_status = order_detail_status
        if order_detail_status == OrderStatusEnum.Cancelado:
            detail.subtotal = 0.0  # Establecer subtotal a 0 para detalles cancelados
            detail.unit_price = 0.0  # Establecer precio unitario a 0
            detail.quantity = 0  # Establecer cantidad a 0
        db.add(detail)
        updated_details.append(OrderDetailItem(
            product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
            quantity=detail.quantity,
            unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
            subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
            order_detail_status=detail.order_detail_status
        ))

    # 5. Recalcular el total de la orden
    all_order_details = db.query(OrdersDetailsModel).filter(
        OrdersDetailsModel.order_id == db_order.id_orders,
        OrdersDetailsModel.order_detail_status != OrderStatusEnum.Cancelado
    ).all()
    
    new_total = sum(float(detail.subtotal) for detail in all_order_details if detail.subtotal is not None)
    db_order.total = new_total  # Actualizar el total en la orden
    db.add(db_order)

    # 6. Confirmar los cambios en la base de datos
    db.commit()
    db.refresh(db_order)  # Refrescar la orden para asegurar que los datos estén actualizados

    return updated_details
#------------------------------------------
#------------------------------------------


#-------------------------------------------
#------------------------------------------

@router.get("/orders/last-order-by-table", response_model=List[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene la última orden de cada mesa del usuario autenticado, incluyendo el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago.")
async def obtener_ultima_orden_por_mesa(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    # Subconsulta: obtener la fecha más reciente por mesa
    subq = (
        db.query(
            OrdersModel.mesa_id,
            func.max(OrdersModel.date_time).label("max_date")
        )
        .filter(OrdersModel.user_id == current_user.id_users)
        .group_by(OrdersModel.mesa_id)
        .subquery()
    )

    # Alias para OrdersModel
    O = aliased(OrdersModel)

    # Consulta principal: obtener las órdenes más recientes por mesa
    last_orders = (
        db.query(O)
        .join(
            subq,
            (O.mesa_id == subq.c.mesa_id) & (O.date_time == subq.c.max_date)
        )
        .options(
            joinedload(O.order_details).joinedload(OrdersDetailsModel.product),
            joinedload(O.user).joinedload(User.user_info),
            joinedload(O.table)
        )
        .all()
    )

    if not last_orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario")

    responses = []
    for db_order in last_orders:
        product_details = [
            OrderDetailItem(
                id_orders_details=detail.id_orders_details,
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status
            )
            for detail in db_order.order_details
        ]

        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        )

        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Agregado para incluir el número de ticket
        )
        responses.append(response)

    return responses


#------------------------------------------
#------------------------------------------

@router.get("/orders/ordenes-ultimas-24-hrs", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene todas las órdenes dentro de 24 horas")
async def dame_todas_las_ordenes_de_las_ultimas_24_horas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Las ultimas 24 horas
    """
    # Calcular la fecha de hace 24 horas
    hace_24_horas = datetime.now() - timedelta(hours=24)
    
    # Obtener las órdenes del usuario autenticado de las últimas 24 horas
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.date_time >= hace_24_horas  # Filtro por las últimas 24 horas
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.user).joinedload(User.user_info),
        joinedload(OrdersModel.table)  # Agregar joinedload para la mesa
    ).all()

    if not db_orders:
        raise HTTPException(status_code=204, detail="No se encontraron órdenes de las últimas 24 horas para este usuario")

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        # Construir la lista de detalles de productos
        product_details = [
            OrderDetailItem(
                id_orders_details=detail.id_orders_details,  # Agregar id_orders_details
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status  # Agregado para incluir el estado del detalle
            )
            for detail in db_order.order_details
        ]

        # Obtener el nombre del restaurante desde UserInfo
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el numero de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
        )

        # Construir la respuesta
        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Agregado para incluir el número de ticket
        )
        responses.append(response)

    return responses


#------------------------------------------
#------------------------------------------

@router.get("/orders/ultima-semana", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene todas las órdenes de los ultimos 7 dias")
async def dame_todas_las_ordenes_de_los_ultimos_7_dias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Ultimos 7 dias
    """
     # Calcular la fecha de hace 7 días
    hace_7_dias = datetime.now() - timedelta(days=7)
    
    # Obtener las órdenes del usuario autenticado de los últimos 7 días
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.date_time >= hace_7_dias  # Filtro por los últimos 7 días
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.user).joinedload(User.user_info),
        joinedload(OrdersModel.table)  # Agregar joinedload para la mesa
    ).all()

    if not db_orders:
        raise HTTPException(status_code=204, detail="No se encontraron órdenes de los últimos 7 días para este usuario")

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        # Construir la lista de detalles de productos
        product_details = [
            OrderDetailItem(
                id_orders_details=detail.id_orders_details,  # Agregar id_orders_details
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status  # Agregado para incluir el estado del detalle
            )
            for detail in db_order.order_details
        ]

        # Obtener el nombre del restaurante desde UserInfo
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el numero de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
        )

        # Construir la respuesta
        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Agregado para incluir el número de ticket
        )
        responses.append(response)

    return responses


#------------------------------------------
#------------------------------------------

@router.get("/orders/ultimo-mes", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene todas las órdenes de los ultimos 30 dias")
async def dame_todas_las_ordenes_de_los_ultimos_30_dias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Ultimos 30 dias
    """
     # Calcular la fecha de hace 7 días
    hace_30_dias = datetime.now() - timedelta(days=30)
    
    # Obtener las órdenes del usuario autenticado de los últimos 7 días
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.date_time >= hace_30_dias  # Filtro por los últimos 7 días
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.user).joinedload(User.user_info),
        joinedload(OrdersModel.table)  # Agregar joinedload para la mesa
    ).all()

    if not db_orders:
        raise HTTPException(status_code=204, detail="No se encontraron órdenes de los últimos 7 días para este usuario")

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        # Construir la lista de detalles de productos
        product_details = [
            OrderDetailItem(
                id_orders_details=detail.id_orders_details,  # Agregar id_orders_details
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status  # Agregado para incluir el estado del detalle
            )
            for detail in db_order.order_details
        ]

        # Obtener el nombre del restaurante desde UserInfo
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el numero de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
        )

        # Construir la respuesta
        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Agregado para incluir el número de ticket
        )
        responses.append(response)

    return responses


#------------------------------------------
#------------------------------------------

@router.get("/orders/entre-fechas", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
description="Obtiene todas las órdenes entre la fecha de inicio y la fecha de fin especificadas")
async def dame_todas_las_ordenes_entre_fechas_establecidas(
    fecha_inicio: str,  # Formato: YYYY-MM-DD
    fecha_fin: str,     # Formato: YYYY-MM-DD
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Entre fechas establecidas
    """
    # Validar y convertir las fechas
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
        
        # Agregar 23:59:59 a la fecha de fin para incluir todo el día
        fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59)
        
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Formato de fecha inválido. Use YYYY-MM-DD (ejemplo: 2024-01-15)"
        )
    
    # Validar que fecha_inicio sea anterior a fecha_fin
    if fecha_inicio_dt > fecha_fin_dt:
        raise HTTPException(
            status_code=400, 
            detail="La fecha de inicio debe ser anterior o igual a la fecha de fin"
        )
    
    # Obtener las órdenes del usuario autenticado entre las fechas especificadas
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.date_time >= fecha_inicio_dt,
        OrdersModel.date_time <= fecha_fin_dt
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.user).joinedload(User.user_info),
        joinedload(OrdersModel.table)
    ).all()

    if not db_orders:
        raise HTTPException(
            status_code=204, 
            detail=f"No se encontraron órdenes entre {fecha_inicio} y {fecha_fin} para este usuario"
        )

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        # Construir la lista de detalles de productos
        product_details = [
            OrderDetailItem(
                id_orders_details=detail.id_orders_details,  # Agregar id_orders_details
                product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
                quantity=detail.quantity,
                unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
                subtotal=float(detail.subtotal) if detail.subtotal is not None else 0.0,
                order_detail_status=detail.order_detail_status  # Agregado para incluir el estado del detalle
            )
            for detail in db_order.order_details
        ]

        # Obtener el nombre del restaurante desde UserInfo
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el numero de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        
        )

        # Construir la respuesta
        response = OrderDetailsByUUIDResponse(
            id_orders=db_order.id_orders,
            mesa_number=mesa_number,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Agregado para incluir el número de ticket
        )
        responses.append(response)

    return responses
