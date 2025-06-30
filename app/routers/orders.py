from fastapi import APIRouter, Depends, HTTPException, status, Form
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from typing import List
import logging
from uuid import uuid4, UUID
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User, Payments
from app.schemas import Orders as OrdersSchema, OrdersResponse, OrdersCreate, OrderCreateResponse, OrderFinalizeResponse, OrdersDetails, OrderDetailsByUUIDResponse, OrderDetailItem
from app.schemas import OrderConfirmationRequest
from app.enums import RoleOrders, TablesEnum, OrderStatusEnum, PlanType, PaymentStatus, SubscriptionAmount, PaymentMethodEnum
from app.db.models import OrdersDetails as OrdersDetailsModel
from app.db.models import Payments as PaymentsModel
from app.repository.auth import get_current_user
from decimal import Decimal
from datetime import datetime

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
#------------------------------------------
#------------------------------------------

@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED,
    description="Crea una nueva orden o añade productos a una orden existente para una mesa especificada. La mesa con número 1 siempre permanece en estado Libre y sus órdenes se finalizan automáticamente. El order_uuid es opcional; si no se proporciona o se envía vacío, se genera uno único. Para pedidos adicionales de la misma mesa, usa el mismo UUID solo si la orden está activa.")
async def crear_orden(
    product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
    quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
    table_number: int = Form(..., description="Número de la mesa a asignar a la orden (la mesa con número 1 siempre permanece disponible y sus órdenes se finalizan automáticamente)"),
    metodo_pago: PaymentMethodEnum = Form(PaymentMethodEnum.efectivo, description="Método de pago de la orden (efectivo, tarjeta, pasarela)"),
    order_uuid: str = Form(None, description="UUID opcional para identificar la orden; si no se proporciona o se envía vacío, se genera uno único. Para pedidos adicionales de la misma mesa, usa el mismo UUID solo si la orden está activa."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        Payments.subscription_end_date >= datetime.utcnow()
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

    # 7. Obtener el código de confirmación más reciente del usuario
    latest_order = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users
    ).order_by(OrdersModel.date_time.desc()).first()
    codigo_confirmacion = latest_order.codigo_confirmacion if latest_order and latest_order.codigo_confirmacion else "000"

    # 8. Determinar el order_uuid y manejar órdenes existentes
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

    # 9. Verificar que los productos existan y pertenezcan al usuario autenticado
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

    # 10. Calcular el total de los nuevos productos
    new_total = 0.0
    for db_product, qty in zip(products, quantities_list):
        new_total += float(db_product.price) * qty

    # 11. Determinar el estado de la orden según la mesa
    order_status = OrderStatusEnum.Finalizado if table_number == 1 else OrderStatusEnum.Pendiente

    # 12. Si existe una orden activa, actualizarla; si no, crear una nueva
    if existing_order:
        # Actualizar la orden existente
        existing_order.total = float(existing_order.total or 0.0) + new_total
        existing_order.product_name = ", ".join(
            list(set(existing_order.product_name.split(", ") + product_names)) if existing_order.product_name else product_names
        )
        existing_order.date_time = datetime.now()
        existing_order.metodo_pago = metodo_pago
        existing_order.order_status = order_status
        existing_order.codigo_confirmacion = codigo_confirmacion
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
        db_order = OrdersModel(
            mesa_id=db_table.id_tables,
            state=RoleOrders.Ocupado,
            order_status=order_status,
            date_time=datetime.now(),
            total=new_total,
            orderscol="Orden creada manualmente",
            user_id=current_user.id_users,
            product_name=", ".join(product_names),
            order_uuid=order_uuid,
            metodo_pago=metodo_pago,
            codigo_confirmacion=codigo_confirmacion
        )
        db.add(db_order)

        # Actualizar el estado de la mesa a Ocupado solo si no es la mesa número 1
        if db_table.state == TablesEnum.Libre and table_number != 1:
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

    # 13. Refrescar la orden para la respuesta
    db_order = existing_order or db_order
    db.refresh(db_order)

    # Crear la respuesta
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
            "product_name": orden.product_name
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

@router.put("/orders/{order_uuid}/cambio_estatus", response_model=OrderFinalizeResponse, status_code=status.HTTP_200_OK)
async def finalizar_orden(
    order_uuid: str,
    order_status: OrderStatusEnum,
    metodo_pago: PaymentMethodEnum,  # Nuevo parámetro para cambiar el método de pago
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

    # Actualizar el estado y el método de pago de todas las órdenes
    for order in db_orders:
        order.order_status = order_status
        order.metodo_pago = metodo_pago  # Actualizar el método de pago
        db.add(order)

        # Si la orden se finaliza, actualizar todos los detalles a Finalizado
        if order_status == OrderStatusEnum.Finalizado:
            order_details = db.query(OrdersDetailsModel).filter(
                OrdersDetailsModel.order_id == order.id_orders
            ).all()
            for detail in order_details:
                if detail.order_detail_status != OrderStatusEnum.Finalizado or detail.order_detail_status != OrderStatusEnum.Cancelado:
                    detail.order_detail_status = OrderStatusEnum.Finalizado
                    db.add(detail)
        
        # Si la orden se canela, cancela todo los detalles
        if order_status == OrderStatusEnum.Cancelado:
            order_details = db.query(OrdersDetailsModel).filter(
                OrdersDetailsModel.order_id == order.id_orders
            ).all()
            for detail in order_details:
                detail.order_detail_status = OrderStatusEnum.Cancelado
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
        order_id=db_orders[0].id_orders,  # Usar la primera orden para la respuesta
        mesa_id=mesa_id,
        order_status=order_status,
        mesa_state=db_table.state
    )

    
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
        metodo_pago=db_order.metodo_pago
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
            mesa_number=db_order.mesa_id,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago
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
    Obtiene todas las órdenes asociadas al usuario autenticado, filtradas por estado si se especifica.
    Retorna una lista con el nombre del restaurante, UUID, fecha, productos, cantidades, precios, subtotales, total y método de pago para cada orden.
    - status: Filtro opcional por estado (Pendiente, EnCocina, Preparado, Cancelado, Completado, Finalizado). Si no se proporciona, devuelve todas las órdenes.
    """
    # Construir la consulta base
    query = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.user).joinedload(User.user_info)
    )

    # Aplicar filtro por estado si se proporciona
    if status:
        query = query.filter(OrdersModel.order_status == status)

    # Ejecutar la consulta
    db_orders = query.all()

    if not db_orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes para este usuario con el estado especificado" if status else "No se encontraron órdenes para este usuario")

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
            mesa_number=db_order.mesa_id,
            # mesa_id=db_order.mesa_id,
            restaurant_name=restaurant_name,
            order_uuid=db_order.order_uuid,
            date_time=db_order.date_time,
            state=db_order.state,
            order_status=db_order.order_status,
            products=product_details,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago
        )
        responses.append(response)

    return responses



#------------------------------------------
#------------------------------------------

@router.put("/orders/{order_uuid}/cambio_details_status", response_model=OrderDetailItem, status_code=status.HTTP_200_OK)
async def finalizar_orden(
    order_uuid: str,
    id_orders_details: int,
    order_detail_status: OrderStatusEnum,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Buscar la orden por UUID y usuario
    db_order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).first()

    if not db_order:
        raise HTTPException(status_code=404, detail=f"No se encontró una orden con UUID {order_uuid} o no te pertenece")

    # 2. Buscar el detalle de la orden por id_orders_details y que pertenezca a la orden encontrada
    db_order_detail = db.query(OrdersDetailsModel).filter(
        OrdersDetailsModel.id_orders_details == id_orders_details,
        OrdersDetailsModel.order_id == db_order.id_orders
    ).first()
    if not db_order_detail:
        raise HTTPException(status_code=404, detail=f"No se encontró el detalle con id {id_orders_details} para el UUID {order_uuid}")

    # Solo permitir modificar si el estado actual NO es Finalizado ni Cancelado
    if db_order_detail.order_detail_status in [OrderStatusEnum.Finalizado, OrderStatusEnum.Cancelado]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede modificar el estado porque el detalle ya está en estado '{db_order_detail.order_detail_status.value}'"
        )
    
    # 3. Cambiar el estado del detalle
    db_order_detail.order_detail_status = order_detail_status
    db.add(db_order_detail)
    db.commit()
    db.refresh(db_order_detail)


    # Refrescar la primera orden y la mesa para la respuesta
    # db.refresh(db_orders[0])
    # db.refresh(db_table)

    return OrderDetailItem(
        product_name=db_order_detail.product.name if db_order_detail.product and db_order_detail.product.name else "Producto desconocido",
        quantity=db_order_detail.quantity,
        unit_price=float(db_order_detail.unit_price) if db_order_detail.unit_price is not None else 0.0,
        subtotal=float(db_order_detail.subtotal) if db_order_detail.subtotal is not None else 0.0,
        order_detail_status=db_order_detail.order_detail_status
    )


#------------------------------------------
#------------------------------------------


@router.put("/confirm", status_code=status.HTTP_200_OK, response_model=OrdersResponse,
description="Actualiza el código de confirmación de una orden y todas las órdenes previas del usuario.")
async def add_confirmation_code(
    request: OrderConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar el código de confirmación
    try:
        OrderConfirmationRequest.validate_codigo_confirmacion(request.codigo_confirmacion)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Buscar la orden por id_orders y user_id, incluyendo las relaciones table y order_details
    order = db.execute(
        select(OrdersModel)
        .options(joinedload(OrdersModel.table), joinedload(OrdersModel.order_details))
        .filter(
            OrdersModel.id_orders == request.id_orders,
            OrdersModel.user_id == current_user.id_users
        )
    ).scalars().first()

    # Verificar si la orden existe
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada o no pertenece al usuario")

    # Actualizar el código de confirmación de la orden específica
    order.codigo_confirmacion = request.codigo_confirmacion

    # Actualizar todas las órdenes previas del usuario con el nuevo código
    db.execute(
        update(OrdersModel)
        .where(OrdersModel.user_id == current_user.id_users)
        .values(codigo_confirmacion=request.codigo_confirmacion)
    )

    # Guardar los cambios
    db.commit()
    db.refresh(order)

    return OrdersResponse.from_orm(order)


