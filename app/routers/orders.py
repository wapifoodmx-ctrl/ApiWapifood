from fastapi import APIRouter, Depends, HTTPException, status, Form
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid
from app.db.database import get_db
from app.db.models import Orders as OrdersModel, Tables as TablesModel, Products as ProductsModel, OrdersDetails as OrderDetailsModel, User
from app.schemas import Orders as OrdersSchema, OrdersResponse, OrdersCreate, OrderCreateResponse, OrderFinalizeResponse
from app.enums import RoleOrders, TablesEnum, OrderStatusEnum
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


@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED,
    description="Crea una nueva orden con detalles para múltiples productos existentes y asigna una mesa especificada. La mesa con ID 1 siempre permanece en estado Libre."
)
async def crear_orden(
    product_ids: str = Form(..., description="Lista de IDs de productos separados por comas (ejemplo: '1,2,3')"),
    quantities: str = Form(..., description="Lista de cantidades separadas por comas (ejemplo: '4,2,1')"),
    mesa_id: int = Form(..., description="ID de la mesa a asignar a la orden (la mesa con ID 1 siempre permanece disponible)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Crea una nueva orden con detalles para múltiples productos existentes y asigna una mesa especificada.
    Los product_ids y quantities deben ser cadenas separadas por comas.
    La mesa con ID 1 siempre permanece en estado Libre, incluso al asignarse a una orden.
    """
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

    # 4. Verificar que la mesa exista y pertenezca al usuario autenticado
    db_table = db.query(TablesModel).filter(
        TablesModel.id_tables == mesa_id,
        TablesModel.user_id == current_user.id_users
    ).first()
    if not db_table:
        raise HTTPException(status_code=404, detail=f"Mesa con ID {mesa_id} no encontrada o no te pertenece")
    
    # 5. Generar UUID para la orden
    if db_table.state == TablesEnum.Ocupado and mesa_id != 1:  # Solo verificar órdenes previas si no es la mesa 1
        # Obtener el UUID de la orden más reciente para esta mesa
        latest_order = db.query(OrdersModel).filter(
            OrdersModel.mesa_id == mesa_id,
            OrdersModel.state == RoleOrders.Ocupado
        ).order_by(OrdersModel.date_time.desc()).first()
        order_uuid = latest_order.order_uuid if latest_order else str(uuid.uuid4())
    else:
        order_uuid = str(uuid.uuid4())  # Nuevo UUID si la mesa está libre o es la mesa 1

    # 6. Verificar que los productos existan y pertenezcan al usuario autenticado
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

    # 7. Calcular el total de la orden
    for db_product, qty in zip(products, quantities_list):
        total_order += float(db_product.price) * qty

    # 8. Crear la orden (Orders) asociada al usuario autenticado
    db_order = OrdersModel(
        mesa_id=mesa_id,
        state=RoleOrders.Ocupado,
        order_status=OrderStatusEnum.Pendiente,  # Estado inicial del pedido
        date_time=datetime.utcnow(),
        total=total_order,
        orderscol="Orden creada manualmente",
        user_id=current_user.id_users,
        product_name=", ".join(product_names),
        order_uuid=order_uuid  # Usar el UUID generado o mantenido
    )
    db.add(db_order)

    # 9. Actualizar el estado de la mesa a Ocupado solo si no es la mesa 1
    if db_table.state == TablesEnum.Libre and mesa_id != 1:
        db_table.state = TablesEnum.Ocupado
    db.commit()
    db.refresh(db_order)
    db.refresh(db_table)

    # 10. Crear los detalles de pedido (OrdersDetails) para cada producto
    for db_product, qty in zip(products, quantities_list):
        unit_price = float(db_product.price)
        subtotal = qty * unit_price

        db_order_detail = OrdersDetailsModel(
            order_id=db_order.id_orders,
            product_id=db_product.id_products,
            quantity=qty,
            unit_price=unit_price,
            subtotal=subtotal
        )
        db.add(db_order_detail)

    db.commit()

    # 11. Refrescar la orden para incluir los detalles y el número de la mesa
    db.refresh(db_order)

    # Crear una instancia del esquema manualmente para incluir mesa_number
    order_response = OrderCreateResponse.from_orm(db_order)
    order_response.mesa_id = db_order.mesa_id
    order_response.mesa_number = db_table.number
    order_response.order_uuid = db_order.order_uuid  # Incluir el UUID en la respuesta

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

    # Convertir los objetos OrdersModel a diccionarios
    orders_dicts = []
    for order in orders:
        order_dict = {
            "id_orders": order.id_orders,
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
                    "subtotal": detail.subtotal if detail.subtotal is not None else 0.0  # Valor por defecto
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
def get_order_summary(
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



@router.put("/orders/{order_id}/finalize", response_model=OrderFinalizeResponse, status_code=status.HTTP_200_OK)
async def finalizar_orden(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_order = db.query(OrdersModel).filter(
        OrdersModel.id_orders == order_id,
        OrdersModel.user_id == current_user.id_users
    ).first()
    if not db_order:
        raise HTTPException(status_code=404, detail=f"Orden con ID {order_id} no encontrada o no te pertenece")

    if not db_order.mesa_id:
        raise HTTPException(status_code=400, detail="La orden no está asociada a una mesa")
    
    db_table = db.query(TablesModel).filter(TablesModel.id_tables == db_order.mesa_id).first()
    if not db_table or db_table.state != TablesEnum.Ocupado:
        raise HTTPException(status_code=400, detail="La mesa no está ocupada o no existe")

    db_order.order_status = OrderStatusEnum.Finalizado
    db_table.state = TablesEnum.Libre

    db.commit()
    db.refresh(db_order)
    db.refresh(db_table)

    return OrderFinalizeResponse(
        message="Orden finalizada y mesa liberada con éxito",
        order_id=order_id,
        mesa_id=db_order.mesa_id,
        order_status=db_order.order_status,
        mesa_state=db_table.state
    )


