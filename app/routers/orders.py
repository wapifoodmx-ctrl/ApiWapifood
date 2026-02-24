from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import select, update, func
from typing import List, Union, Dict, Any
import logging
from uuid import uuid4, UUID
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User, Payments, WebOrders, WebOrderDetails, UserInfo
from app.schemas import Orders as OrdersSchema, OrdersResponse, OrdersCreate, OrderCreateResponse, OrderFinalizeResponse, OrdersDetails, OrderDetailsByUUIDResponse, OrderDetailItem, OrderCommentResponse, OrderCommentsRequest, OrderFullCommentsResponse, WebItemInput, WebCustomerInput, WebOrderCreateRequest, WebDetailResponse, WebOrderResponse, WebConfigToggle
from app.enums import RoleOrders, TablesEnum, OrderStatusEnum, PlanType, PaymentStatus, SubscriptionAmount, PaymentMethodEnum
from app.db.models import OrdersDetails as OrdersDetailsModel
from app.db.models import Payments as PaymentsModel, UserConfirmationCode
from app.repository.auth import get_current_user
from decimal import Decimal
from datetime import datetime,  timedelta
import random
from sqlalchemy import desc
import os
import requests
from app.enums import WebStatusOpciones, WebOrderAction


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

# Esquema OAuth2 para el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED,
    description="Crea una nueva orden o añade productos a una orden existente para una mesa especificada. La mesa con número 1 siempre permanece en estado Libre y sus órdenes inician como PuntoDeVenta. El order_uuid es opcional; si no se proporciona o se envía vacío, se genera uno único. Para pedidos adicionales de la misma mesa, usa el mismo UUID solo si la orden está activa (no finalizada ni cancelada).")
async def crear_orden(
    product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
    quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
    descuento: str = Form("0", description="Descuento aplicado al total, en formato de cadena (ejemplo: '10%', '5.00')"),
    descuento_details: str = Form("0", description="Descuento aplicado a la orden_detail, en formato de cadena (ejemplo: '10%', '5.00')"),
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
    
    # --- INICIO DE LA MODIFICACIÓN ---
    # Guardar el número de productos para validaciones posteriores
    num_productos = len(product_ids_list)
    # --- FIN DE LA MODIFICACIÓN ---
    
        # Validar descuento de la orden
    if "%" in descuento:
        try:
            valor = float(descuento.replace("%", ""))
        except ValueError:
            raise HTTPException(status_code=400, detail="El descuento porcentual debe ser un número válido")
        if valor < 0 or valor > 100:
            raise HTTPException(status_code=400, detail="El descuento porcentual debe estar entre 0% y 100%")
    else:
        try:
            valor = float(descuento)
        except ValueError:
            raise HTTPException(status_code=400, detail="El descuento debe ser un número válido")
        if valor < 0:
            raise HTTPException(status_code=400, detail="El descuento no puede ser menor a 0")

    # --- INICIO DE LA MODIFICACIÓN ---
    # Validar descuento_details para cada producto
    descuento_details_list = [] # Inicializar lista

    # Si el usuario envía "0" (default) o "" (empty value), creamos una lista de ceros
    if descuento_details == "0" or descuento_details == "":
        descuento_details_list = ["0"] * num_productos
    else:
        # Si envía valores específicos (ej. "10,0,5%"), los separamos
        descuento_details_list_temp = descuento_details.split(",")
        # Y validamos que la longitud coincida con el número de productos
        if len(descuento_details_list_temp) != num_productos:
            raise HTTPException(status_code=400, detail="El número de descuentos por detalle debe coincidir con el número de productos")
        descuento_details_list = descuento_details_list_temp
    # --- FIN DE LA MODIFICACIÓN ---

    # Validar cada descuento_details
    for idx, desc_det in enumerate(descuento_details_list):
        desc_det = desc_det.strip()
        if "%" in desc_det:
            try:
                valor_det = float(desc_det.replace("%", ""))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"El descuento porcentual del detalle debe ser válido en el producto {product_ids_list[idx]}")
            if valor_det < 0 or valor_det > 100:
                raise HTTPException(status_code=400, detail=f"El descuento porcentual del detalle debe estar entre 0% y 100% en el producto {product_ids_list[idx]}")
        else:
            try:
                valor_det = float(desc_det)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"El descuento del detalle debe ser válido en el producto {product_ids_list[idx]}")
            if valor_det < 0:
                raise HTTPException(status_code=400, detail=f"El descuento del detalle no puede ser menor a 0 en el producto {product_ids_list[idx]}")

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
        SubscriptionAmount.PLAN_INAUGURACION.value: 3,
        SubscriptionAmount.PLAN_100.value: 3,
        SubscriptionAmount.PLAN_200.value: 16,
        SubscriptionAmount.PLAN_300.value: 26,
        SubscriptionAmount.BASICO_IMPRESORA.value: 3,  # Ajusta según tu lógica
        SubscriptionAmount.RESTAURANTE_IMPRESORA.value: 16,  # Ajusta según tu lógica
        SubscriptionAmount.PLUS_RESTAURANTE_IMPRESORA.value: 26  # Ajusta según tu lógica
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
        
    # 9. Calcular el total de los nuevos productos aplicando descuento_details
    new_total = 0.0
    subtotals = []
    for idx, (db_product, qty) in enumerate(zip(products, quantities_list)):
        unit_price = float(db_product.price)
        subtotal = qty * unit_price

        # Aplicar descuento_details al subtotal
        desc_det = descuento_details_list[idx].strip()
        if "%" in desc_det:
            valor_det = float(desc_det.replace("%", ""))
            descuento_aplicado = subtotal * (valor_det / 100)
        else:
            descuento_aplicado = float(desc_det)
        subtotal -= descuento_aplicado
        if subtotal < 0:
            subtotal = 0.0

        subtotals.append(subtotal)
        new_total += subtotal

    # Aplicar descuento general al total
    if descuento and descuento != "0":
        if "%" in descuento:
            valor = float(descuento.replace("%", ""))
            descuento_aplicado = new_total * (valor / 100)
        else:
            descuento_aplicado = float(descuento)
        new_total -= descuento_aplicado
        if new_total < 0:
            new_total = 0.0

    # 10. Si existe una orden activa, actualizarla; si no, crear una nueva
    if existing_order:
        existing_order.total = float(existing_order.total or 0.0) + new_total
        existing_order.product_name = ", ".join(
            list(set(existing_order.product_name.split(", ") + product_names)) if existing_order.product_name else product_names
        )
        existing_order.date_time = datetime.now()
        existing_order.metodo_pago = metodo_pago

        # Añadir los nuevos detalles con descuento_details aplicado al subtotal
        for idx, (db_product, qty) in enumerate(zip(products, quantities_list)):
            unit_price = float(db_product.price)
            subtotal = subtotals[idx]
            db.add(OrdersDetailsModel(
                order_id=existing_order.id_orders,
                product_id=db_product.id_products,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
                order_detail_status=OrderStatusEnum.Pendiente,
                descuento_details=descuento_details_list[idx].strip()
            ))
        db.flush()
        db.add(existing_order)
    else:
        initial_status = OrderStatusEnum.PuntoDeVenta if table_number == 1 else OrderStatusEnum.Pendiente
        db_order = OrdersModel(
            mesa_id=db_table.id_tables,
            state=RoleOrders.Ocupado if table_number != 1 else RoleOrders.Libre,
            order_status=initial_status,
            date_time=datetime.now(),
            descuento=descuento,
            total=new_total,
            orderscol="Orden creada manualmente",
            product_name=", ".join(product_names),
            user_id=current_user.id_users,
            order_uuid=order_uuid,
            metodo_pago=metodo_pago
        )
        db.add(db_order)

        if db_table.number != 1 and db_table.state == TablesEnum.Libre:
            db_table.state = TablesEnum.Ocupado

        db.commit()
        db.refresh(db_order)

        # Crear los detalles de pedido con descuento_details aplicado al subtotal
        for idx, (db_product, qty) in enumerate(zip(products, quantities_list)):
            unit_price = float(db_product.price)
            subtotal = subtotals[idx]
            db_order_detail = OrdersDetailsModel(
                order_id=db_order.id_orders,
                product_id=db_product.id_products,
                quantity=qty,
                unit_price=unit_price,
                descuento_details=descuento_details_list[idx].strip(),
                subtotal=subtotal,
                order_detail_status=OrderStatusEnum.Pendiente,
            )
            db.add(db_order_detail)

    db.commit()
    db.refresh(db_table)

    # # 11. Refrescar la orden para la respuesta y actualizar estado final
    # db_order = existing_order or db_order
    # db.refresh(db_order)

    # # 12. Crear respuesta con el número de mesa
    # order_response = OrderCreateResponse.from_orm(db_order)
    # order_response.mesa_id = db_order.mesa_id
    # order_response.mesa_number = db_table.number
    # order_response.order_uuid = db_order.order_uuid

    # return order_response
    if existing_order:
        db_order = existing_order
    
    # Ahora sí, refrescamos la orden para tener los datos más recientes
    db.refresh(db_order)

    # -----------------------------------------------------------------------
    # 🚨 CORRECCIÓN OBLIGATORIA: Construcción manual de la respuesta
    # -----------------------------------------------------------------------
    # Esto evita el error "product_name Field required"
    
    details_response = []
    for detail in db_order.order_details:
        # Obtenemos el nombre del producto de la relación (si está cargada)
        p_name = "Desconocido"
        if detail.product:
            p_name = detail.product.name
        
        details_response.append({
            "id_orders_details": detail.id_orders_details,
            "product_id": detail.product_id,
            "product_name": p_name, # 👈 AQUÍ ASIGNAMOS EL NOMBRE MANUALMENTE
            "quantity": detail.quantity,
            "unit_price": detail.unit_price,
            "subtotal": detail.subtotal,
            "descuento_details": detail.descuento_details,
            "order_detail_status": detail.order_detail_status,
            "comments": detail.comments # Agregamos los comentarios
        })

    # Retornamos el diccionario directo (FastAPI lo convertirá al Schema automáticamente)
    return {
        "id_orders": db_order.id_orders,
        "order_uuid": db_order.order_uuid,
        "mesa_id": db_order.mesa_id,
        "mesa_number": db_table.number,
        "state": db_order.state,
        "order_status": db_order.order_status,
        "date_time": db_order.date_time,
        "descuento": db_order.descuento,
        "total": db_order.total,
        "orderscol": db_order.orderscol,
        "user_id": db_order.user_id,
        "product_name": db_order.product_name,
        "metodo_pago": db_order.metodo_pago,
        "ticket_number": db_order.ticket_number,
        "order_details": details_response # 👈 Lista construida manualmente
    }
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
            "descuento": order.descuento if order.descuento is not None else 0.0,  # Valor por defecto
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
                    "descuento_details": detail.descuento_details if detail.descuento_details is not None else "0",  # Valor por defecto
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
            "descuento": orden.descuento if orden.descuento else 0.0,
            "total": float(orden.total) if orden.total else 0.0,
            "product_name": orden.product_name,
            "ticket_number": orden.ticket_number #if orden.ticket_number else "Sin número de ticket"
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

    # ---------------------------------------------------------------
    # 🛑 NUEVA VALIDACIÓN DE ESTADOS (Lo que pediste)
    # ---------------------------------------------------------------
    for order in db_orders:
        # CASO 1: Si la orden ya estaba CANCELADA, prohibir pasar a Finalizada
        if order.order_status == OrderStatusEnum.Cancelado:
            if order_status == OrderStatusEnum.Finalizado:
                raise HTTPException(
                    status_code=400, 
                    detail=f"La orden {order.id_orders} está CANCELADA y no puede reactivarse a Finalizada."
                )
            # Nota: Si intentas pasar de Cancelada a Cancelada otra vez, no pasa nada, el código sigue.

        # CASO 2: Si la orden ya estaba FINALIZADA
        if order.order_status == OrderStatusEnum.Finalizado:
            # Solo permitimos cambiarla si el nuevo estado es CANCELADO (cliente se fue, error de dedo, etc.)
            if order_status != OrderStatusEnum.Cancelado:
                raise HTTPException(
                    status_code=400, 
                    detail=f"La orden {order.id_orders} ya está FINALIZADA. Solo se permite cambiar a CANCELADO."
                )

    # ---------------------------------------------------------------

    # 🆕 Obtener el siguiente número de ticket solo si el estado es "Finalizado"
    # (Si venimos de Finalizado -> Cancelado, esto se salta y no asigna nuevo ticket, lo cual es correcto)
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
            # Si ya tenía ticket (ej. re-finalizando algo raro), mantenemos, si no, asignamos
            if not order.ticket_number: 
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
        
        # Si la orden se cancela (incluso si venía de Finalizado), poner todo en CERO
        if order_status == OrderStatusEnum.Cancelado:
            order.total = Decimal(0.00) # Resetear total orden
            
            order_details = db.query(OrdersDetailsModel).filter(
                OrdersDetailsModel.order_id == order.id_orders
            ).all()
            for detail in order_details:
                detail.order_detail_status = OrderStatusEnum.Cancelado
                detail.unit_price = 0.0  # Establecer el precio unitario a 0
                detail.subtotal = 0.0
                detail.quantity = 0  # Establecer la cantidad a 0 (OJO: Esto borra la evidencia de qué pidieron)
                db.add(detail)

    # Liberar la mesa si el estado es Finalizado y no es la mesa número 1
    # Nota: Si pasamos de Finalizado a Cancelado, la mesa ya debería haberse liberado antes, 
    # pero no hace daño dejar la lógica, aunque para Cancelado, la mesa también debería quedar Libre/NoDisponible según tu lógica de negocio.
    if order_status == OrderStatusEnum.Finalizado and db_table.number != 1:
        db_table.state = TablesEnum.NoDisponible # O la lógica que uses para liberar

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


# -----------------------------------------------------------------------------
# 📺 ENDPOINT GET KIOSCO: VER ÓRDENES ACTIVAS CON TICKET
# -----------------------------------------------------------------------------
@router.get("/kiosko", response_model=List[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK)
def get_kiosko_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene las órdenes generadas por Kiosco (o cualquier orden con Ticket activo).
    Filtra órdenes que:
    1. Tienen ticket_number asignado.
    2. NO están Canceladas.
    """
    # Filtramos las órdenes que tienen ticket y son del día de hoy
    today = datetime.now().replace(hour=0, minute=0, second=0)
    
    orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.ticket_number.is_not(None), # Clave: Tiene ticket
        OrdersModel.date_time >= today,
        OrdersModel.order_status != OrderStatusEnum.Cancelado
    ).order_by(OrdersModel.ticket_number.desc()).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.table),
        joinedload(OrdersModel.user).joinedload(User.user_info)
    ).all()

    # Formatear respuesta
    responses = []
    for order in orders:
        product_details = [
            OrderDetailItem(
                id_orders_details=d.id_orders_details,
                product_id=d.product_id,
                product_name=d.product.name if d.product else "N/A", # ✅ Evita el error de Pydantic
                quantity=d.quantity,
                unit_price=float(d.unit_price or 0),
                subtotal=float(d.subtotal or 0),
                order_detail_status=d.order_detail_status,
                descuento_details=d.descuento_details or "0",
                comments=d.comments # 👈 AGREGADO: Para ver los comentarios en el Kiosco/Cocina
            ) for d in order.order_details
        ]
        
        restaurant_name = order.user.user_info.nombre_restaurante if (order.user and order.user.user_info) else "Kiosco"
        mesa_num = order.table.number if order.table else 0

        resp = OrderDetailsByUUIDResponse(
            id_orders=order.id_orders,
            mesa_number=mesa_num,
            restaurant_name=restaurant_name,
            order_uuid=order.order_uuid,
            date_time=order.date_time,
            state=order.state,
            order_status=order.order_status,
            products=product_details,
            descuento=order.descuento or 0.0,
            total=float(order.total or 0),
            metodo_pago=order.metodo_pago,
            ticket_number=order.ticket_number
        )
        responses.append(resp)

    return responses



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
            product_id=detail.product_id,  # Agregar el product_id
            product_name=detail.product.name if detail.product and detail.product.name else "Producto desconocido",
            quantity=detail.quantity,
            unit_price=float(detail.unit_price) if detail.unit_price is not None else 0.0,
            descuento_details=detail.descuento_details if detail.descuento_details is not None else "0",  # Valor por defecto
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
        mesa_number=mesa_number, 
        restaurant_name=restaurant_name,
        order_uuid=db_order.order_uuid,
        date_time=db_order.date_time,
        state=db_order.state,
        order_status=db_order.order_status,
        products=product_details,
        descuento=db_order.descuento if db_order.descuento is not None else 0.0,
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
                descuento_details=detail.descuento_details if detail.descuento_details is not None else "0",  # Valor por defecto
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
            descuento=db_order.descuento if db_order.descuento is not None else 0.0,
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
                descuento_details=detail.descuento_details if detail.descuento_details is not None else "0",  # Valor por defecto
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
            descuento=db_order.descuento if db_order.descuento is not None else 0.0,
            total=float(db_order.total) if db_order.total is not None else 0.0,
            metodo_pago=db_order.metodo_pago,
            ticket_number=db_order.ticket_number  # Incluir el ticket_number si está disponible
        )
        responses.append(response)

    return responses



#------------------------------------------
#------------------------------------------

INVENTORY_API_URL = os.getenv("INVENTORY_API_URL", "https://api-micro.wapifood.com") # O tu URL local


# -----------------------------------------------------------------------------
# 🛑 ENDPOINT CORREGIDO: CAMBIO DETALLES (COCINA / MERMA)
# -----------------------------------------------------------------------------
@router.put("/orders/{order_uuid}/cambio_details_status", response_model=List[OrderDetailItem], status_code=status.HTTP_200_OK)
async def finalizar_orden(
    order_uuid: str,
    id_orders_details: str = Form(...),  # Cadena de IDs separados por comas
    order_detail_status: OrderStatusEnum = Form(...),
    is_merma: bool = Form(False), # Bandera de Merma
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    try:
        id_orders_details_list = [int(id_str) for id_str in id_orders_details.split(",")]
    except ValueError:
        raise HTTPException(status_code=422, detail="IDs inválidos")

    # 1. Buscar la orden
    db_order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).first()

    if not db_order: raise HTTPException(404, detail="Orden no encontrada")

    # 2. Buscar detalles
    db_order_details = db.query(OrdersDetailsModel).filter(
        OrdersDetailsModel.id_orders_details.in_(id_orders_details_list),
        OrdersDetailsModel.order_id == db_order.id_orders
    ).all()

    if len(db_order_details) != len(id_orders_details_list): 
        raise HTTPException(404, detail="No se encontraron todos los detalles")

    # 3. Validaciones
    for detail in db_order_details:
        if detail.order_detail_status == OrderStatusEnum.Cancelado:
             raise HTTPException(400, detail="Detalle ya cancelado.")
        if detail.order_detail_status == OrderStatusEnum.Finalizado and order_detail_status != OrderStatusEnum.Cancelado:
            raise HTTPException(400, detail="Producto finalizado solo puede pasar a CANCELADO.")

    updated_details = []
    
    # 4. Aplicar cambios
    for detail in db_order_details:
        detail.order_detail_status = order_detail_status
        
        # SI SE CANCELA
        if order_detail_status == OrderStatusEnum.Cancelado:
            # Registrar Merma en Inventario
            if is_merma:
                try:
                    payload = {"product_id": detail.product_id, "quantity": detail.quantity}
                    headers = {"Authorization": f"Bearer {token}"}
                    requests.post(f"{INVENTORY_API_URL}/inventory/record-loss/", json=payload, headers=headers)
                except Exception as e:
                    print(f"⚠️ Error registrando merma: {e}")

            # Poner montos en 0 para que no sumen al total
            detail.subtotal = 0.0
            detail.unit_price = 0.0
            detail.quantity = 0 
        
        db.add(detail)
        updated_details.append(OrderDetailItem(
            id_orders_details=detail.id_orders_details, # Importante devolver ID
            product_name=detail.product.name if detail.product else "Desconocido",
            quantity=detail.quantity,
            unit_price=float(detail.unit_price or 0),
            descuento_details=detail.descuento_details or "0",
            subtotal=float(detail.subtotal or 0),
            order_detail_status=detail.order_detail_status
        ))

    # ---------------------------------------------------------
    # 🚀 CORRECCIÓN CLAVE: RECALCULAR TOTAL CON DESCUENTO
    # ---------------------------------------------------------
    # 1. Sumamos todos los subtotales ACTIVOS (no cancelados)
    all_active = db.query(OrdersDetailsModel).filter(
        OrdersDetailsModel.order_id == db_order.id_orders,
        OrdersDetailsModel.order_detail_status != OrderStatusEnum.Cancelado
    ).all()
    
    raw_subtotal = sum(float(d.subtotal or 0) for d in all_active)
    
    # 2. Re-aplicamos el descuento que ya tenía la orden
    new_total = raw_subtotal
    current_discount = db_order.descuento
    
    if current_discount and current_discount != "0":
        if "%" in current_discount:
            try:
                pct = float(current_discount.replace("%", ""))
                descuento_valor = raw_subtotal * (pct / 100)
                new_total -= descuento_valor
            except: pass
        else:
            try:
                val = float(current_discount)
                new_total -= val
            except: pass
            
    if new_total < 0: new_total = 0.0
    
    # 3. Guardamos el nuevo total corregido
    db_order.total = Decimal(new_total)
    db.add(db_order)

    # Cancelar orden completa si todo está cancelado
    all_details = db.query(OrdersDetailsModel).filter(OrdersDetailsModel.order_id == db_order.id_orders).all()
    if all_details and all(d.order_detail_status == OrderStatusEnum.Cancelado for d in all_details):
        db_order.order_status = OrderStatusEnum.Cancelado
        db_order.total = 0.0
        db.add(db_order)

    db.commit()
    db.refresh(db_order)
    
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
                product_id=detail.product_id,
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
            description="Obtiene todas las órdenes de los últimos 7 días")
async def dame_todas_las_ordenes_de_los_ultimos_7_dias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Últimos 7 días
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
                id_orders_details=detail.id_orders_details,
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

        # Obtener el número de mesa, usar 0 si no está disponible
        mesa_number = db_order.table.number if db_order.table and db_order.table.number else 0

        # Construir la respuesta
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
            ticket_number=db_order.ticket_number
        )
        responses.append(response)

    return responses

#------------------------------------------
#------------------------------------------

@router.get("/orders/ultimo-mes", response_model=list[OrderDetailsByUUIDResponse], status_code=status.HTTP_200_OK,
            description="Obtiene todas las órdenes de los últimos 30 días")
async def dame_todas_las_ordenes_de_los_ultimos_30_dias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las órdenes asociadas al usuario autenticado.
    Últimos 30 días
    """
    # Calcular la fecha de hace 30 días
    hace_30_dias = datetime.now() - timedelta(days=30)
    
    # Obtener las órdenes del usuario autenticado de los últimos 30 días
    db_orders = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.date_time >= hace_30_dias
    ).options(
        joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
        joinedload(OrdersModel.user).joinedload(User.user_info),
        joinedload(OrdersModel.table)
    ).all()

    if not db_orders:
        raise HTTPException(status_code=204, detail="No se encontraron órdenes de los últimos 30 días para este usuario")

    # Construir la lista de respuestas
    responses = []
    for db_order in db_orders:
        # Construir la lista de detalles de productos
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

        # Obtener el nombre del restaurante desde UserInfo
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el número de mesa, usar 0 si no está disponible
        mesa_number = db_order.table.number if db_order.table and db_order.table.number else 0

        # Construir la respuesta
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
            ticket_number=db_order.ticket_number
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
            db_order.table.number if db_order.table and db_order.table.number else 0
        
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

#------------------------------------------ mostrar ultimos pedidos 


# Mapa de planes basado en tu archivo payments.py y tu solicitud anterior
PLAN_TO_TABLES_MAP = {
    "inauguracion": 3,
    "basico": 3,
    "profesional": 16,
    "empresarial": 26,
    "basico_impresora": 3,
    "restaurante_impresora": 16,
    "plus_restaurante_impresora": 26
}

@router.get("/orders/latest-by-plan", response_model=List[OrdersResponse], status_code=status.HTTP_200_OK)
def get_latest_orders_by_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene las últimas órdenes permitidas según el plan ACTIVO en Payments.
    Excluye la Mesa 1 y limita la cantidad a (Total Mesas Plan - 1).
    """

    # 1. Obtener el Plan Activo desde la tabla Payments
    current_time = datetime.utcnow()
    
    active_payment = (
        db.query(Payments)
        .filter(
            Payments.user_id == current_user.id_users,
            Payments.status == PaymentStatus.COMPLETED,
            Payments.subscription_end_date > current_time
        )
        .order_by(desc(Payments.date))
        .first()
    )

    # 2. Determinar el nombre del plan
    if active_payment:
        # Si 'plan' es un objeto Enum, obtenemos su valor (.value), si es string lo usamos directo
        user_plan_name = active_payment.plan.value if hasattr(active_payment.plan, "value") else active_payment.plan
    else:
        user_plan_name = "basico"
    # 3. Calcular el límite
    # Obtenemos el total de mesas permitidas para ese plan (ej: 3)
    total_tables_allowed = PLAN_TO_TABLES_MAP.get(str(user_plan_name).lower(), 3) # Default a 3 si falla
    
    # El límite de órdenes a mostrar es igual al número de mesas permitidas (menos la mesa 1 si se requiere)
    # En tu lógica original restabas 1 (total_tables_allowed - 1). 
    # Si tienes 3 mesas (1, 2, 3) y la 1 es POS, te quedan 2 mesas (2 y 3).
    # Entonces query_limit debería ser 2.
    query_limit = total_tables_allowed - 1 if total_tables_allowed > 1 else 0
    
    # Debug
    # print(f"Plan: {user_plan_name} | Límite: {query_limit}")

    if query_limit <= 0:
        return []

    # 4. Consulta a la Base de Datos (CORREGIDA)
    orders = (
        db.query(OrdersModel)
        .join(TablesModel, OrdersModel.mesa_id == TablesModel.id_tables)
        .filter(OrdersModel.user_id == current_user.id_users)
        .filter(TablesModel.number != 1)  # Excluir Mesa 1
        .order_by(OrdersModel.date_time.desc())
        .limit(query_limit)
        .options(
            joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
            joinedload(OrdersModel.table)  # <--- CORRECCIÓN AQUÍ: Usamos .table, no .mesa
        )
        .all()
    )

    if not orders:
        return []

    # 5. Formateo de respuesta
    orders_dicts = []
    for order in orders:
        # <--- CORRECCIÓN AQUÍ: Usamos order.table
        mesa_number = order.table.number if order.table else None

        order_dict = {
            "id_orders": order.id_orders,
            "mesa_number": mesa_number,
            "state": order.state,
            "order_status": order.order_status,
            "date_time": order.date_time,
            "descuento": order.descuento if order.descuento is not None else 0.0,
            "total": float(order.total) if order.total is not None else 0.0,
            "orderscol": order.orderscol,
            "user_id": order.user_id,
            "order_uuid": order.order_uuid,
            "product_name": order.product_name or "Sin nombre",
            "ticket_number": order.ticket_number if order.ticket_number else "Sin número de ticket",
            "details": [
                {
                    "quantity": detail.quantity,
                    "unit_price": detail.unit_price if detail.unit_price is not None else 0.0,
                    "descuento_details": detail.descuento_details if detail.descuento_details is not None else "0",
                    "subtotal": detail.subtotal if detail.subtotal is not None else 0.0,
                    "order_detail_status": detail.order_detail_status
                }
                for detail in order.order_details
            ]
        }
        orders_dicts.append(order_dict)

    return [OrdersResponse.model_validate(order_dict) for order_dict in orders_dicts]


# -----------------------------------------------------------------------------
# 🏪 ENDPOINT KIOSCO: CREAR ORDEN + TICKET AUTOMÁTICO
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 🏪 ENDPOINT KIOSCO: CREAR ORDEN + TICKET AUTOMÁTICO
# -----------------------------------------------------------------------------
@router.post("/kiosko", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def crear_orden_kiosko(
    product_ids: str = Form(..., description="Lista de IDs separados por comas"),
    quantities: str = Form(..., description="Lista de cantidades separadas por comas"),
    metodo_pago: PaymentMethodEnum = Form(PaymentMethodEnum.tarjeta), # Kiosco suele ser tarjeta
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Crea una orden desde el Kiosco.
    DIFERENCIA: Asigna número de ticket INMEDIATAMENTE y estado 'Pendiente' (directo a cocina).
    Usa la Mesa 1 (Punto de Venta) para asignar la venta.
    """
    # 1. Parsear listas
    try:
        p_ids = [int(x) for x in product_ids.split(",")]
        qtys = [int(x) for x in quantities.split(",")]
    except: 
        raise HTTPException(400, "Formato inválido en IDs o cantidades")
    
    if len(p_ids) != len(qtys): 
        raise HTTPException(400, "La cantidad de productos no coincide con las cantidades")

    # 2. Generar Ticket Inmediato
    # Buscamos el último ticket del usuario y sumamos 1
    last_ticket = db.query(OrdersModel).filter(
        OrdersModel.user_id == current_user.id_users,
        OrdersModel.ticket_number.is_not(None)
    ).order_by(OrdersModel.ticket_number.desc()).first()
    
    next_ticket = (int(last_ticket.ticket_number) + 1) if (last_ticket and last_ticket.ticket_number) else 1

    # 3. Calcular Total y Validar Productos
    total = 0.0
    products_db = [] # Guardamos los objetos aquí para usarlos al final (nombre del producto)
    product_names = []
    
    for idx, pid in enumerate(p_ids):
        prod = db.query(ProductsModel).filter(ProductsModel.id_products == pid).first()
        if not prod: 
            raise HTTPException(404, f"Producto {pid} no encontrado")
        
        # Validar propiedad del producto
        if prod.owner_id != current_user.id_users:
            raise HTTPException(403, f"No tienes permiso sobre el producto {pid}")

        subtotal = float(prod.price) * qtys[idx]
        total += subtotal
        
        # Guardamos la info necesaria para no volver a consultar la BD
        products_db.append({"prod": prod, "qty": qtys[idx], "sub": subtotal})
        product_names.append(prod.name)

    # 4. Crear Orden (Cabecera)
    # Buscamos la Mesa 1 del usuario para asignarla (Kiosco = POS)
    mesa_kiosco = db.query(TablesModel).filter(
        TablesModel.user_id == current_user.id_users, 
        TablesModel.number == 1
    ).first()
    
    if not mesa_kiosco: 
        raise HTTPException(400, "No se encontró la Mesa 1 (requerida para Kiosco)")

    new_order = OrdersModel(
        mesa_id=mesa_kiosco.id_tables,
        state=RoleOrders.Ocupado,
        order_status=OrderStatusEnum.Pendiente, # Directo a cocina
        date_time=datetime.now(),
        descuento="0",
        total=total,
        orderscol="Orden Kiosco",
        product_name=", ".join(product_names),
        user_id=current_user.id_users,
        order_uuid=str(uuid4()),
        metodo_pago=metodo_pago,
        ticket_number=next_ticket # <--- ASIGNACIÓN DE TICKET AL CREAR
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 5. Crear Detalles (Renglones de la orden)
    for item in products_db:
        det = OrdersDetailsModel(
            order_id=new_order.id_orders,
            product_id=item["prod"].id_products,
            quantity=item["qty"],
            unit_price=float(item["prod"].price),
            subtotal=item["sub"],
            order_detail_status=OrderStatusEnum.Pendiente,
            descuento_details="0",
            # comments="" # Descomenta si ya migraste la columna comments
        )
        db.add(det)
    
    # 6. Descontar Inventario
    # Intentamos descontar, si falla el microservicio, no detenemos la venta pero lo logueamos
    try:
        items_inv = [{"product_id": p["prod"].id_products, "quantity": p["qty"]} for p in products_db]
        headers = {"Authorization": f"Bearer {token}"}
        # Nota: verify=False para evitar errores de certificado SSL locales
        requests.post(
            f"{INVENTORY_API_URL}/inventory/discount-stock-multiple/", 
            json={"items": items_inv, "ticket_number": next_ticket}, 
            headers=headers,
            verify=False 
        )
    except Exception as e:
        print(f"⚠️ Error al descontar inventario en Kiosco: {e}")

    db.commit()
    db.refresh(new_order) # Refrescamos para obtener los IDs de los detalles creados

    # 7. Construir Respuesta Manualmente (CORRECCIÓN DEL ERROR PYDANTIC)
    # Mapeamos los datos manualmente para asegurar que 'product_name' esté presente
    details_response = []
    
    for detail in new_order.order_details:
        # Buscamos el nombre en nuestra lista local 'products_db' para eficiencia
        prod_obj = next((item["prod"] for item in products_db if item["prod"].id_products == detail.product_id), None)
        prod_name_str = prod_obj.name if prod_obj else "Desconocido"

        details_response.append({
            "id_orders_details": detail.id_orders_details,
            "product_id": detail.product_id,
            "product_name": prod_name_str, # <--- AQUÍ SE SOLUCIONA EL ERROR "Field required"
            "quantity": detail.quantity,
            "unit_price": detail.unit_price,
            "subtotal": detail.subtotal,
            "descuento_details": detail.descuento_details,
            "order_detail_status": detail.order_detail_status,
            # "comments": detail.comments # Descomenta si ya migraste
        })

    # Retornamos el diccionario final
    return {
        "id_orders": new_order.id_orders,
        "order_uuid": new_order.order_uuid,
        "mesa_id": new_order.mesa_id,
        "mesa_number": 1, 
        "state": new_order.state,
        "order_status": new_order.order_status,
        "date_time": new_order.date_time,
        "descuento": new_order.descuento,
        "total": new_order.total,
        "orderscol": new_order.orderscol,
        "user_id": new_order.user_id,
        "product_name": new_order.product_name,
        "metodo_pago": new_order.metodo_pago,
        "ticket_number": new_order.ticket_number,
        "order_details": details_response # <--- Lista construida manualmente
    }




# =============================================================================
# 📝 ENDPOINTS DE COMENTARIOS (NOTAS DE COCINA)
# =============================================================================
# =============================================================================
# 📝 ENDPOINTS DE COMENTARIOS (Reciclando 'orderscol' para el General)
# =============================================================================

@router.post("/{order_uuid}/comments", status_code=status.HTTP_200_OK, 
             description="Agrega comentarios. El 'general' se guarda en la columna existente 'orderscol")
async def agregar_comentarios_orden(
    order_uuid: str,
    payload: OrderCommentsRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar la orden
    db_order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).first()

    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada o sin permisos")

    # ---------------------------------------------------------
    # A. Guardar Comentario General (Reciclando 'orderscol')
    # ---------------------------------------------------------
    if payload.general_comment:
        # Nota: 'orderscol' suele tener info de origen (ej: "Orden Kiosco"). 
        # No queremos borrar eso, así que lo concatenamos o reemplazamos según prefieras.
        
        current_text = db_order.orderscol if db_order.orderscol else ""
        
        # Lógica: Si el comentario ya existe en el texto, no lo duplicamos.
        # Si es un texto nuevo, lo agregamos con un separador " | Notas: "
        if "Notas:" not in current_text:
             db_order.orderscol = f"{current_text} | Notas: {payload.general_comment}"
        else:
             # Si ya había notas, reemplazamos la parte de las notas (lógica simple: sobrescribir todo para actualizar)
             # Opción simple: Sobrescribir conservando el origen si es posible, o simplemente reemplazar:
             # db_order.orderscol = payload.general_comment # (Usa esto si no te importa borrar "Orden Kiosco")
             
             # Opción Segura (Concatenar):
             parts = current_text.split(" | Notas: ")
             origen = parts[0]
             db_order.orderscol = f"{origen} | Notas: {payload.general_comment}"
             
        db.add(db_order)

    # ---------------------------------------------------------
    # B. Guardar Comentarios de Detalles (Columna 'comments')
    # ---------------------------------------------------------
    comentarios_agregados = 0
    if payload.details_comments:
        ids_a_modificar = [item.id_orders_details for item in payload.details_comments]
        
        db_details = db.query(OrdersDetailsModel).filter(
            OrdersDetailsModel.order_id == db_order.id_orders,
            OrdersDetailsModel.id_orders_details.in_(ids_a_modificar)
        ).all()

        details_map = {d.id_orders_details: d for d in db_details}

        for input_comment in payload.details_comments:
            detail_obj = details_map.get(input_comment.id_orders_details)
            if detail_obj:
                detail_obj.comments = input_comment.comment
                db.add(detail_obj)
                comentarios_agregados += 1

    db.commit()

    return {
        "message": "Comentarios actualizados",
        "general_updated": bool(payload.general_comment),
        "details_updated_count": comentarios_agregados
    }


@router.get("/{order_uuid}/comments", response_model=OrderFullCommentsResponse, status_code=status.HTTP_200_OK, 
            description="Obtiene comentarios. Extrae el general de 'orderscol'.")
async def obtener_comentarios_orden(
    order_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Buscar orden
    db_order = db.query(OrdersModel).filter(
        OrdersModel.order_uuid == order_uuid,
        OrdersModel.user_id == current_user.id_users
    ).options(joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product)).first()

    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Extraer Comentario General de 'orderscol'
    # 'orderscol' se ve así: "Orden Kiosco | Notas: Entregar atrás"
    full_text = db_order.orderscol if db_order.orderscol else ""
    general_comm = ""
    
    if " | Notas: " in full_text:
        parts = full_text.split(" | Notas: ")
        if len(parts) > 1:
            general_comm = parts[1] # Tomamos solo lo que está después del separador
    elif full_text and "Orden" not in full_text: 
        # Si el texto NO parece ser un status del sistema, asumimos que es todo un comentario
        general_comm = full_text

    # 3. Formatear lista de detalles
    lista_detalles = []
    for detail in db_order.order_details:
        lista_detalles.append({
            "id_orders_details": detail.id_orders_details,
            "product_name": detail.product.name if detail.product else "Desconocido",
            "comment": detail.comments if detail.comments else ""
        })

    # 4. Retornar
    return OrderFullCommentsResponse(
        order_uuid=db_order.order_uuid,
        general_comment=general_comm,
        details_comments=lista_detalles

    )


@router.post("/web/create", status_code=status.HTTP_201_CREATED, summary="Crea una Pre-Orden Web")
async def crear_pedido_web(
    restaurant_uuid: str, 
    payload: WebOrderCreateRequest,
    # 👇 AQUÍ ESTÁ LA MAGIA: Esto crea la lista desplegable en la documentación
    status_inicial: WebStatusOpciones = Query(
        WebStatusOpciones.PENDIENTE, 
        description="Selecciona el estatus inicial de la orden"
    ),
    db: Session = Depends(get_db)
):
    from app.db.models import User, WebOrders, WebOrderDetails
    
    # 1. Buscar al Dueño
    owner_user = db.query(User).filter(User.uuid == restaurant_uuid).first()
    if not owner_user:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    
    owner_id = owner_user.id_users

    # -------------------------------------------------------------
    # 🔢 CÁLCULO DEL FOLIO WEB (Por Restaurante)
    # -------------------------------------------------------------
    last_order = db.query(WebOrders).filter(
        WebOrders.user_id == owner_id 
    ).order_by(WebOrders.folio_web.desc()).first()

    next_folio = (last_order.folio_web + 1) if (last_order and last_order.folio_web) else 1
    # -------------------------------------------------------------

    # 2. Validar Productos
    total_order = 0.0
    items_to_create = []

    for item in payload.items:
        prod = db.query(ProductsModel).filter(ProductsModel.id_products == item.product_id).first()
        if not prod: raise HTTPException(404, detail=f"Producto {item.product_id} no existe")
        if prod.owner_id != owner_id: raise HTTPException(400, detail="Producto ajeno")

        subtotal = float(prod.price) * item.quantity
        total_order += subtotal
        
        items_to_create.append({
            "product": prod, "qty": item.quantity, "sub": subtotal, "comment": item.comment
        })

    # 3. Crear Cabecera
    new_order_uuid = str(uuid4()) 
    full_address = f"{payload.customer.direccion}, CP: {payload.customer.codigo_postal}"

    new_web_order = WebOrders(
        uuid_restaurant=restaurant_uuid,
        order_uuid=new_order_uuid,
        folio_web=next_folio,
        user_id=owner_id,
        customer_name=payload.customer.nombre,
        customer_phone=payload.customer.telefono,
        customer_address=full_address,
        customer_notes=payload.customer.referencias,
        total=total_order,
        
        # 👇 AQUÍ USAMOS LA OPCIÓN SELECCIONADA EN LA LISTA
        status=status_inicial.value, 
        
        created_at=datetime.now()
    )
    db.add(new_web_order)
    db.commit()
    db.refresh(new_web_order)

    # 4. Guardar Detalles
    for data in items_to_create:
        detail = WebOrderDetails(
            web_order_id=new_web_order.id_web_orders,
            product_id=data["product"].id_products,
            quantity=data["qty"],
            unit_price=float(data["product"].price),
            subtotal=data["sub"],
            comment=data["comment"]
        )
        db.add(detail)
    
    db.commit()

    return {
        "message": "Pre-orden creada exitosamente", 
        "order_uuid": new_web_order.order_uuid,
        "folio_web": next_folio,
        "status": new_web_order.status # Confirmamos el estatus guardado
    }



# En app/routers/orders.py
# =============================================================================
# 1. LISTAR PEDIDOS WEB (GET)
# =============================================================================
@router.get("/web/list", response_model=List[WebOrderResponse])
def listar_pedidos_web(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    El dueño ve sus pedidos web pendientes.
    Muestra el UUID seguro y el Folio Web (1, 2, 3...).
    """
    from app.db.models import WebOrders # Importación segura

    # Traemos las órdenes de la tabla NUEVA
    web_orders = db.query(WebOrders).filter(
        WebOrders.user_id == current_user.id_users,
        WebOrders.status == "PENDIENTE" 
    ).order_by(WebOrders.created_at.desc()).all()

    # Construimos la respuesta mapeando manualmente para evitar errores
    results = []
    for order in web_orders:
        details_list = []
        for d in order.details:
            # Validación segura de producto eliminado
            p_name = d.product.name if d.product else "Producto Eliminado"
            
            details_list.append(WebDetailResponse(
                product_name=p_name,
                quantity=d.quantity,
                unit_price=d.unit_price,
                subtotal=d.subtotal,
                comment=d.comment or ""
            ))
        
        # 👇 VALIDACIONES SEGURAS (Para no romper con datos viejos)
        uuid_safe = order.order_uuid if order.order_uuid else "SIN-UUID"
        folio_safe = order.folio_web if order.folio_web else 0

        results.append(WebOrderResponse(
            id_web_orders=order.id_web_orders,
            order_uuid=uuid_safe,       # UUID Único
            folio_web=folio_safe,       # Folio Secuencial (1, 2, 3)
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            customer_address=order.customer_address,
            customer_notes=order.customer_notes or "",
            total=order.total,
            status=order.status,
            created_at=order.created_at,
            details=details_list
        ))

    return results


# =============================================================================
# 2. ACEPTAR PRE-ORDEN (POST) - Lógica Completa
# =============================================================================
@router.post("/web/accept/{web_order_uuid}", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def aceptar_orden_web(
    web_order_uuid: str, # Recibimos el UUID, no el ID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Convierte una Pre-Orden Web en una Orden Real de Cocina.
    """
    from app.db.models import WebOrders, Orders, OrdersDetails, Tables, Products
    
    # 1. Buscar por UUID y verificar que sea del usuario actual
    web_order = db.query(WebOrders).filter(
        WebOrders.order_uuid == web_order_uuid, # Búsqueda por UUID
        WebOrders.user_id == current_user.id_users 
    ).first()

    if not web_order:
        raise HTTPException(status_code=404, detail="Pre-orden no encontrada o no te pertenece")
    
    if web_order.status != "PENDIENTE":
        raise HTTPException(status_code=400, detail=f"Esta orden ya está en estatus {web_order.status}")

    # 2. Configuración Inicial (Mesa y Ticket)
    # Buscar Mesa 1 (Punto de Venta / Virtual)
    mesa_kiosco = db.query(Tables).filter(
        Tables.user_id == current_user.id_users, 
        Tables.number == 1
    ).first()
    
    if not mesa_kiosco:
        raise HTTPException(400, "No se encontró la Mesa 1 para asignar la orden")

    # Generar Siguiente Número de Ticket
    last_ticket = db.query(Orders).filter(
        Orders.user_id == current_user.id_users,
        Orders.ticket_number.is_not(None)
    ).order_by(Orders.ticket_number.desc()).first()
    
    next_ticket = (int(last_ticket.ticket_number) + 1) if (last_ticket and last_ticket.ticket_number) else 1

    # 3. Construcción del String 'orderscol' con el PREFIJO DELIVERY
    info_cliente = (
        f"Cliente: {web_order.customer_name} | "
        f"Tel: {web_order.customer_phone} | "
        f"Dir: {web_order.customer_address} | "
        f"Notas: {web_order.customer_notes}"
    )
    
    # Prefijo requerido por el Frontend
    texto_final_delivery = f"external-menu-delivery-order, {info_cliente}"

    # Recopilar nombres de productos
    nombres_prods = [d.product.name for d in web_order.details if d.product]

    # 4. Crear la ORDEN REAL (Tabla Orders)
    real_order = Orders(
        mesa_id=mesa_kiosco.id_tables,
        state=RoleOrders.Ocupado,
        order_status=OrderStatusEnum.Pendiente, # Directo a Cocina
        date_time=datetime.now(),
        descuento="0",
        total=web_order.total,
        orderscol=texto_final_delivery, # ✅ Prefijo + Datos
        product_name=", ".join(nombres_prods),
        user_id=current_user.id_users,
        order_uuid=str(uuid4()), # UUID nuevo para la orden real
        metodo_pago=PaymentMethodEnum.efectivo,
        ticket_number=next_ticket
    )
    
    db.add(real_order)
    db.flush() # Flush para obtener el ID

    # 5. Migrar Detalles y Comentarios
    details_response = []
    items_inventory = []

    for web_item in web_order.details:
        # Crear detalle real
        new_detail = OrdersDetails(
            order_id=real_order.id_orders,
            product_id=web_item.product_id,
            quantity=web_item.quantity,
            unit_price=web_item.unit_price,
            subtotal=web_item.subtotal,
            order_detail_status=OrderStatusEnum.Pendiente,
            descuento_details="0",
            comments=web_item.comment # ✅ Migramos comentario ("sin cebolla")
        )
        db.add(new_detail)
        
        # Datos para inventario
        items_inventory.append({
            "product_id": web_item.product_id, 
            "quantity": web_item.quantity
        })

        # Respuesta manual
        p_name = web_item.product.name if web_item.product else "Desconocido"
        details_response.append({
            "id_orders_details": 0, # Se generará al commit
            "product_id": web_item.product_id,
            "product_name": p_name,
            "quantity": web_item.quantity,
            "unit_price": web_item.unit_price,
            "subtotal": web_item.subtotal,
            "descuento_details": "0",
            "order_detail_status": OrderStatusEnum.Pendiente,
            "comments": web_item.comment
        })

    # 6. Descontar Inventario
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Asegúrate de que INVENTORY_API_URL esté definido arriba en tu archivo o impórtalo
        requests.post(
            f"{INVENTORY_API_URL}/inventory/discount-stock-multiple/", 
            json={"items": items_inventory, "ticket_number": next_ticket}, 
            headers=headers,
            verify=False 
        )
    except Exception as e:
        print(f"⚠️ Error descontando inventario web: {e}")

    # 7. Finalizar
    web_order.status = "ACEPTADO" # Marcamos como aceptada
    
    db.commit()
    db.refresh(real_order)

    return {
        "id_orders": real_order.id_orders,
        "order_uuid": real_order.order_uuid,
        "mesa_id": real_order.mesa_id,
        "mesa_number": 1,
        "state": real_order.state,
        "order_status": real_order.order_status,
        "date_time": real_order.date_time,
        "descuento": real_order.descuento,
        "total": real_order.total,
        "orderscol": real_order.orderscol,
        "user_id": real_order.user_id,
        "product_name": real_order.product_name,
        "metodo_pago": real_order.metodo_pago,
        "ticket_number": real_order.ticket_number,
        "order_details": details_response
    }

# =============================================================================
# 2. PROCESAR PRE-ORDEN (ACEPTAR O DESCARTAR) - Devuelve datos de envío
# =============================================================================

# 👇 NOTA: Quitamos "response_model=..." para que nos deje devolver los datos del cliente libres
@router.post("/web/process/{web_order_uuid}", status_code=status.HTTP_200_OK)
async def gestionar_orden_web(
    web_order_uuid: str, 
    accion: WebOrderAction = Query(..., description="Elige 'ACEPTAR' para enviar a cocina o 'DESCARTAR' para rechazarla."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Gestiona una Pre-Orden Web:
    - DESCARTAR: Cambia estatus a 'RECHAZADO' (Desaparece de la lista).
    - ACEPTAR: Convierte a Orden Real, genera Ticket, descuenta Inventario y devuelve datos de envío.
    """
    from app.db.models import WebOrders, Orders, OrdersDetails, Tables, Products
    
    # 1. Buscar por UUID y verificar permisos
    web_order = db.query(WebOrders).filter(
        WebOrders.order_uuid == web_order_uuid,
        WebOrders.user_id == current_user.id_users 
    ).first()

    if not web_order:
        raise HTTPException(status_code=404, detail="Pre-orden no encontrada o no te pertenece")
    
    if web_order.status != "PENDIENTE":
        raise HTTPException(status_code=400, detail=f"Esta orden ya fue procesada (Estatus: {web_order.status})")

    # =========================================================================
    # 🔴 OPCIÓN A: DESCARTAR LA ORDEN
    # =========================================================================
    if accion == WebOrderAction.DESCARTAR:
        web_order.status = "RECHAZADO" # Cambiamos estatus
        db.commit()
        return {"message": f"La orden {web_order.folio_web} ha sido descartada y ocultada de la lista."}

    # =========================================================================
    # 🟢 OPCIÓN B: ACEPTAR LA ORDEN (Toda la lógica de cocina)
    # =========================================================================
    elif accion == WebOrderAction.ACEPTAR:
        
        # 2. Configuración Inicial (Mesa y Ticket)
        mesa_kiosco = db.query(Tables).filter(
            Tables.user_id == current_user.id_users, 
            Tables.number == 1
        ).first()
        
        if not mesa_kiosco: raise HTTPException(400, "Falta Mesa 1")

        last_ticket = db.query(Orders).filter(
            Orders.user_id == current_user.id_users,
            Orders.ticket_number.is_not(None)
        ).order_by(Orders.ticket_number.desc()).first()
        
        next_ticket = (int(last_ticket.ticket_number) + 1) if (last_ticket and last_ticket.ticket_number) else 1

        # 3. Construcción del String con Prefijo
        info_cliente = (
            f"Cliente: {web_order.customer_name} | "
            f"Tel: {web_order.customer_phone} | "
            f"Dir: {web_order.customer_address} | "
            f"Notas: {web_order.customer_notes}"
        )
        texto_final_delivery = f"external-menu-delivery-order, {info_cliente}"

        nombres_prods = [d.product.name for d in web_order.details if d.product]

        # 4. Crear la ORDEN REAL
        real_order = Orders(
            mesa_id=mesa_kiosco.id_tables,
            state=RoleOrders.Ocupado,
            order_status=OrderStatusEnum.Pendiente,
            date_time=datetime.now(),
            descuento="0",
            total=web_order.total,
            orderscol=texto_final_delivery,
            product_name=", ".join(nombres_prods),
            user_id=current_user.id_users,
            order_uuid=str(uuid4()), # Este es el UUID nuevo de la orden POS
            metodo_pago=PaymentMethodEnum.efectivo,
            ticket_number=next_ticket
        )
        db.add(real_order)
        db.flush()

        # 👇 NUEVA LÍNEA MAGICA: Vinculamos la orden web con la orden real
        web_order.pos_order_uuid = real_order.order_uuid

        # 5. Migrar Detalles
        details_response = []
        items_inventory = []

        for web_item in web_order.details:
            new_detail = OrdersDetails(
                order_id=real_order.id_orders,
                product_id=web_item.product_id,
                quantity=web_item.quantity,
                unit_price=web_item.unit_price,
                subtotal=web_item.subtotal,
                order_detail_status=OrderStatusEnum.Pendiente,
                descuento_details="0",
                comments=web_item.comment
            )
            db.add(new_detail)
            
            items_inventory.append({"product_id": web_item.product_id, "quantity": web_item.quantity})
            
            p_name = web_item.product.name if web_item.product else "Desconocido"
            details_response.append({
                "id_orders_details": 0,
                "product_id": web_item.product_id,
                "product_name": p_name,
                "quantity": web_item.quantity,
                "unit_price": web_item.unit_price,
                "subtotal": web_item.subtotal,
                "descuento_details": "0",
                "order_detail_status": OrderStatusEnum.Pendiente,
                "comments": web_item.comment
            })

        # 6. Descontar Inventario
        try:
            headers = {"Authorization": f"Bearer {token}"}
            requests.post(
                f"{INVENTORY_API_URL}/inventory/discount-stock-multiple/", 
                json={"items": items_inventory, "ticket_number": next_ticket}, 
                headers=headers, 
                verify=False
            )
        except: pass

        # 7. Finalizar y cambiar estatus
        web_order.status = "ACEPTADO"
        
        db.commit()
        db.refresh(real_order)

        # 👇 AQUÍ DEVOLVEMOS TODOS LOS DATOS + LA INFO DE ENVÍO
        return {
            "id_orders": real_order.id_orders,
            "order_uuid": real_order.order_uuid, # UUID nuevo
            "web_order_uuid": web_order.order_uuid, # UUID original de la pre-orden web
            "mesa_id": real_order.mesa_id,
            "mesa_number": 1,
            "state": real_order.state,
            "order_status": real_order.order_status,
            "date_time": real_order.date_time,
            "descuento": real_order.descuento,
            "total": real_order.total,
            "orderscol": real_order.orderscol,
            "user_id": real_order.user_id,
            "product_name": real_order.product_name,
            "metodo_pago": real_order.metodo_pago,
            "ticket_number": real_order.ticket_number,
            "order_details": details_response,
            
            # ✨ NUEVO: Mapeo de los datos del cliente para el FrontEnd ✨
            "customer_data": {
                "nombre": web_order.customer_name,
                "telefono": web_order.customer_phone,
                "direccion": web_order.customer_address,
                "referencias": web_order.customer_notes
            }
        }


# =============================================================================
# 3. CONSULTAR DATOS DE ENVÍO (Expira en 12 horas)
# =============================================================================
@router.get("/web/delivery-info/{uuid_busqueda}", status_code=status.HTTP_200_OK, summary="Obtener datos de envío (Expira en 12h)")
async def obtener_datos_envio(
    uuid_busqueda: str, # 👈 Ahora acepta cualquier UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la información de envío.
    Puedes buscar enviando el UUID de la pre-orden web O el UUID de la orden real.
    Expira en 12 horas por seguridad.
    """
    from app.db.models import WebOrders
    from datetime import datetime, timedelta

    # 1. Buscar la orden web por CUALQUIERA de los dos UUIDs
    web_order = db.query(WebOrders).filter(
        # 👇 BUSCA POR EL UUID WEB --- O --- POR EL UUID DE COCINA 👇
        (WebOrders.order_uuid == uuid_busqueda) | (WebOrders.pos_order_uuid == uuid_busqueda),
        WebOrders.user_id == current_user.id_users
    ).first()

    if not web_order:
        raise HTTPException(status_code=200, detail="Orden no encontrada o no te pertenece.")

    # 2. Lógica de Expiración (12 horas)
    tiempo_transcurrido = datetime.now() - web_order.created_at
    doce_horas = timedelta(hours=12)

    # Si ya pasaron 12 horas
    if tiempo_transcurrido > doce_horas:
        return {
            "web_order_uuid": web_order.order_uuid,
            "pos_order_uuid": web_order.pos_order_uuid,
            "folio_web": web_order.folio_web,
            "status": web_order.status,
            "created_at": web_order.created_at,
            "message": "Los datos del cliente han sido ocultados por seguridad tras 12 horas.",
            "customer_data": None
        }

    # 3. Si está dentro del tiempo, devuelve todo
    return {
        "web_order_uuid": web_order.order_uuid,
        "pos_order_uuid": web_order.pos_order_uuid, # Te confirmamos cuál es la orden real
        "folio_web": web_order.folio_web,
        "status": web_order.status,
        "created_at": web_order.created_at,
        "message": "Datos de envío disponibles.",
        "customer_data": {
            "nombre": web_order.customer_name,
            "telefono": web_order.customer_phone,
            "direccion": web_order.customer_address,
            "referencias": web_order.customer_notes
        }
    }



# =============================================================================
# 🟢 CONFIGURACIÓN WEB: TOGGLE DE DELIVERY
# =============================================================================

# 1. GET PÚBLICO: El frontend web consulta si hay delivery disponible
@router.get("/web/status/delivery", status_code=status.HTTP_200_OK, summary="Consulta si el restaurante tiene Delivery activo")
async def consultar_estado_delivery(
    restaurant_uuid: str, # El UUID público del restaurante
    db: Session = Depends(get_db)
):
    from app.db.models import User, WebConfig
    
    # Buscar al dueño
    owner_user = db.query(User).filter(User.uuid == restaurant_uuid).first()
    if not owner_user:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    # Buscar su configuración
    config = db.query(WebConfig).filter(WebConfig.user_id == owner_user.id_users).first()
    
    # Si no tiene configuración guardada aún, asumimos que SÍ hay delivery (True)
    estado = config.is_delivery_active if config else False

    return {
        "restaurant_uuid": restaurant_uuid,
        "is_delivery_active": estado
    }


# 2. PUT PRIVADO: El dueño prende o apaga el Delivery
@router.put("/web/status/delivery", status_code=status.HTTP_200_OK, summary="Enciende o apaga el Delivery")
async def cambiar_estado_delivery(
    payload: WebConfigToggle, # Recibe { "is_delivery_active": true/false }
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.db.models import WebConfig
    
    # Buscamos si el dueño ya tiene una fila de configuración
    config = db.query(WebConfig).filter(WebConfig.user_id == current_user.id_users).first()

    if config:
        # Si ya existe, solo actualizamos el True/False
        config.is_delivery_active = payload.is_delivery_active
    else:
        # Si es la primera vez que toca el botón, creamos la fila
        config = WebConfig(
            user_id=current_user.id_users,
            is_delivery_active=payload.is_delivery_active
        )
        db.add(config)

    db.commit()

    return {
        "message": "Estado de delivery actualizado",
        "is_delivery_active": config.is_delivery_active
    }