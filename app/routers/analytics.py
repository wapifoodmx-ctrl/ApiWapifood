from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.db.models import Orders, Payments, User, RoleEnum, OrderAnalytics, OrdersDetails, OrdersDetails as OrdersDetailsModel
from app.db.models import Orders as OrdersModel
from app.oauth import get_current_user
from app.db.database import get_db
from dateutil.relativedelta import relativedelta
from typing import Optional, List
#from app.db.models import Restaurante
from app.schemas import Metric, AnalyticsResponse, Orders as VentasSchema, VentasBasicSchema, OrderDetailsByUUIDResponse, OrderDetailItem
from zoneinfo import ZoneInfo


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def calculate_percentage_change(current: float, previous: float) -> float:
    """
    Calcula el cambio porcentual entre el valor actual y el anterior.
    Retorna 0 si el valor anterior es 0 para evitar división por cero.
    """
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


#------------------------------------------------------------------
#-----------------------------------------------------------------


# ... (importaciones y otras partes del archivo se mantienen iguales)
@router.get("/dashboard", response_model=AnalyticsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene métricas clave para el dashboard del usuario autenticado usando Orders.
    Muestra métricas acumulativas desde la primera orden hasta la fecha actual.
    """
    # Obtener la fecha de la primera orden del usuario
    first_order = db.query(Orders.date_time).filter(
        Orders.user_id == current_user.id_users
    ).order_by(Orders.date_time.asc()).first()

    if not first_order:
        return AnalyticsResponse(
            total_sales=Metric(value=0.0, change=0.0, change_label=""),
            total_orders=Metric(value=0, change=0.0, change_label=""),
            new_customers=Metric(value=0, change=0.0, change_label=""),
            average_daily_sales=Metric(value=0.0, change=0.0, change_label="")
        )

    start_date = first_order[0]
    today = datetime.utcnow()  # Usar UTC para consistencia con Orders.date_time

    # Usar el final del día actual (23:59:59) para incluir todas las órdenes del día
    today = today.replace(hour=23, minute=59, second=59, microsecond=0)

    # Asegurarse de que las fechas sean comparables (sin zona horaria)
    start_date = start_date.replace(tzinfo=None)
    today = today.replace(tzinfo=None)

    # Calcular el número de días en el período total (días completos)
    days_in_period = (today - start_date).days + 1  # +1 para incluir el día actual

    # 1. Ventas totales (usando Orders.total)
    total_sales = (
        db.query(func.sum(Orders.total))
        .filter(
            Orders.date_time >= start_date,
            Orders.date_time <= today,
            Orders.user_id == current_user.id_users
        )
        .scalar() or 0.0
    )
    # Convertir total_sales a float si es Decimal
    total_sales = float(total_sales) if total_sales is not None else 0.0

    # 2. Pedidos totales (número de pedidos)
    total_orders = (
        db.query(func.count(Orders.id_orders))
        .filter(
            Orders.date_time >= start_date,
            Orders.date_time <= today,
            Orders.user_id == current_user.id_users
        )
        .scalar() or 0
    )

    # 3. Clientes nuevos (ajustado para contar usuarios distintos con rol 'client')
    new_customers = (
        db.query(func.count(Orders.user_id.distinct()))
        .filter(
            Orders.date_time >= start_date,
            Orders.date_time <= today,
            Orders.user_id == current_user.id_users,
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.rol == RoleEnum.client)
            )
        )
        .scalar() or 0
    )

    # 4. Ventas promedio por día (ventas totales / número de días)

    #average_daily_sales = (total_sales / days_in_period) if days_in_period > 0 else 0.0
    average_daily_sales = (total_sales / total_orders) if total_orders> 0 else 0.0

    # Construir la respuesta
    return AnalyticsResponse(
        total_sales=Metric(
            value=float(total_sales),
            change=0.0,
            change_label=""
        ),
        total_orders=Metric(
            value=float(total_orders),
            change=0.0,
            change_label=""
        ),
        new_customers=Metric(
            value=float(new_customers),
            change=0.0,
            change_label=""
        ),
        average_daily_sales=Metric(
            value=float(average_daily_sales),
            change=0.0,
            change_label=""
        )
    )

# -------------------------------------------------------------------------
#-----------------------------------------------------------------------


@router.get("/get-analytics-details", response_model=list[VentasSchema])
async def obtenemos_fechas_total(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las ventas de usuario."""
    #ventas = db.query(Orders).all()  # Muestra todas las órdenes
    ventas = (
         db.query(Orders)
         .filter(Orders.user_id == current_user.id_users)
         .all()
    )

    # Verificar si hay ventas para el usuario
    if not ventas:
        raise HTTPException(status_code=404, detail="No se encontrarron ventas para este usuario")
    
    # Convertir las ventas a diccionarios
    ventas_dicts = []
    for venta in ventas:
        venta_dict = {
            "id_orders": venta.id_orders,
            "state": venta.state,
            "date_time": venta.date_time.isoformat() if venta.date_time else None,
            "total": venta.total or 0.0,  # Valor por defecto si es None
            "orderscol": venta.orderscol or "Sin descripción",
            "product_name": venta.product_name or "Sin nombre",  # Valor por defecto
            "user_id": venta.user_id,
            "order_details": [
            {
                "id_orders_details": d.id_orders_details,
                "order_id": d.order_id,
                "product_id": d.product_id,
                "quantity": d.quantity,
                "unit_price": d.unit_price,
                "subtotal": d.subtotal,
            }
            for d in getattr(venta, "order_details", [])
        ]

        }
        ventas_dicts.append(venta_dict)
    return [VentasSchema.model_validate(venta_dict) for venta_dict in ventas_dicts]

# -------------------------------------------------------------------------
#-----------------------------------------------------------------------


@router.get("/get-analytics-basic", response_model=list[VentasBasicSchema])
async def obtenemos_fechas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las ventas de usuario."""
    #ventas = db.query(Orders).all()  # Muestra todas las órdenes
    ventas = (
         db.query(Orders)
         .filter(Orders.user_id == current_user.id_users)
         .all()
    )

    # Verificar si hay ventas para el usuario
    if not ventas:
        raise HTTPException(status_code=404, detail="No se encontrarron ventas para este usuario")
    
    # Convertir las ventas a diccionarios
    ventas_dicts = []
    for venta in ventas:
        venta_dict = {
            "id_orders": venta.id_orders,
            "date": venta.date_time.isoformat() if venta.date_time else None,
            "value": venta.total or 0.0,
        }
        ventas_dicts.append(venta_dict)
    return [VentasBasicSchema.model_validate(venta_dict) for venta_dict in ventas_dicts]

#-------------------------------------------------------------------
#-------------------------------------------------------------------




@router.post("/generate-analytics")
async def generate_analytics(
    period_type: str,  # "month" o "week"
    end_date: str = None,  # Formato: "YYYY-MM-DD"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar period_type
    if period_type not in ["month", "week"]:
        raise HTTPException(status_code=400, detail="period_type debe ser 'month' o 'week'")

    # Obtener la fecha de la primera venta como start_date
    first_sale = db.query(Orders.date_time).filter(
        Orders.user_id == current_user.id_users
    ).order_by(Orders.date_time.asc()).first()

    if not first_sale:
        raise HTTPException(status_code=404, detail="No se encontraron ventas para este usuario")

    start = first_sale[0]  # Extraer el valor de la tupla (date_time)

    # Obtener la fecha de la última venta o usar end_date si se proporciona
    last_sale = db.query(Orders.date_time).filter(
        Orders.user_id == current_user.id_users
    ).order_by(Orders.date_time.desc()).first()

    if not last_sale:
        raise HTTPException(status_code=404, detail="No se encontraron ventas para este usuario")

    end = last_sale[0] if end_date is None else datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    # Validar que end_date (si se proporciona) sea posterior a la primera venta
    if end_date and start >= end:
        raise HTTPException(
            status_code=400,
            detail=f"end_date ({end_date}) debe ser posterior a la fecha de la primera venta ({start.strftime('%Y-%m-%d %H:%M:%S')})"
        )

    # Asegurarse de que las fechas sean UTC (aunque aquí usamos sin zona horaria)
    start = start.replace(tzinfo=None)
    end = end.replace(tzinfo=None)

    # Eliminar datos existentes para este usuario y period_type en el rango de fechas
    db.query(OrderAnalytics).filter(
        OrderAnalytics.user_id == current_user.id_users,
        OrderAnalytics.period_type == period_type,
        OrderAnalytics.period_start >= start,
        OrderAnalytics.period_start <= end
    ).delete()

    # Generar períodos (mensuales o semanales)
    current_date = start
    while current_date <= end:
        if period_type == "month":
            period_end = current_date + relativedelta(months=1) - timedelta(days=1)
            period_end = min(period_end, end)
        else:  # week
            period_end = current_date + timedelta(days=6)
            period_end = min(period_end, end)

        # Buscar órdenes en este período para el usuario
        orders = db.query(Orders).filter(
            Orders.user_id == current_user.id_users,
            Orders.date_time >= current_date,
            Orders.date_time <= period_end
        ).all()

        # Calcular métricas
        total_orders = len(orders)
        total_revenue = sum(order.total for order in orders) if orders else 0.0
        total_products_sold = 0

        # Calcular la cantidad de productos vendidos (desde OrdersDetails)
        for order in orders:
            details = db.query(OrdersDetails).filter(OrdersDetails.order_id == order.id_orders).all()
            total_products_sold += sum(detail.quantity for detail in details)

        # Guardar en OrderAnalytics
        analytics_entry = OrderAnalytics(
            period_start=current_date,
            period_type=period_type,
            total_orders=total_orders,
            total_revenue=float(total_revenue),
            total_products_sold=total_products_sold,
            user_id=current_user.id_users
        )
        db.add(analytics_entry)

        # Avanzar al siguiente período
        if period_type == "month":
            current_date = current_date + relativedelta(months=1)
        else:
            current_date = current_date + timedelta(days=7)

    db.commit()
    return {"message": f"Datos analíticos generados para {period_type} desde {start.strftime('%Y-%m-%d %H:%M:%S')} hasta {end.strftime('%Y-%m-%d %H:%M:%S')}"}


#------------------------------------------------------------------
#-----------------------------------------------------------------


@router.get("/get-analytics")
async def get_analytics(
    period_type: str,  # "month" o "week"
    start_date: str,   # Formato: "YYYY-MM-DD"
    end_date: str,     # Formato: "YYYY-MM-DD"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar period_type
    if period_type not in ["month", "week"]:
        raise HTTPException(status_code=400, detail="period_type debe ser 'month' o 'week'")

    # Parsear las fechas
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    if start >= end:
        raise HTTPException(status_code=400, detail="start_date debe ser anterior a end_date")

    # Asegurarse de que las fechas sean UTC
    start = start.replace(tzinfo=None)
    end = end.replace(tzinfo=None)

    # Obtener datos analíticos
    analytics = db.query(OrderAnalytics).filter(
        OrderAnalytics.user_id == current_user.id_users,
        OrderAnalytics.period_type == period_type,
        OrderAnalytics.period_start >= start,
        OrderAnalytics.period_start <= end
    ).order_by(OrderAnalytics.period_start.asc()).all()

    if not analytics:
        raise HTTPException(status_code=404, detail="No se encontraron datos analíticos para este período")

    return [
        {
            "period_start": entry.period_start.isoformat(),
            "total_orders": entry.total_orders,
            "total_revenue": entry.total_revenue,
            "total_products_sold": entry.total_products_sold
        }
        for entry in analytics
    ]

#------------------------------------------------------------------
#-----------------------------------------------------------------


#CONSULTAR LAS FECHAS EN BASE A AÑO, MES Y SEMANA 


class SalesResponse(BaseModel):
    period: str  # year, month o week
    total_sales: float

# Endpoint 1: Ventas agrupadas por año
@router.get("/ventas_por_año", response_model=List[SalesResponse], status_code=status.HTTP_200_OK,
            description="Obtiene las ventas totales agrupadas por año entre la fecha de inicio y la fecha de fin especificadas")
async def ventas_por_año(
    fecha_inicio: str,  # Formato: YYYY-MM-DD
    fecha_fin: str,     # Formato: YYYY-MM-DD
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve las ventas totales agrupadas por año en el rango de fechas especificado.
    """
    try:
        start = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        end = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    if start >= end:
        raise HTTPException(status_code=400, detail="fecha_inicio debe ser anterior a fecha_fin")

    # Consulta para obtener las ventas agrupadas por año
    sales = (
        db.query(
            func.extract('year', Orders.date_time).label('year'),
            func.sum(Orders.total).label('total_sales')
        )
        .filter(
            Orders.user_id == current_user.id_users,
            Orders.date_time >= start,
            Orders.date_time <= end
        )
        .group_by(func.extract('year', Orders.date_time))
        .order_by(func.extract('year', Orders.date_time))
        .all()
    )

    if not sales:
        raise HTTPException(status_code=404, detail="No se encontraron ventas en el rango especificado")

    return [{"period": str(int(year)), "total_sales": float(total_sales)} for year, total_sales in sales]
#------------------------------------------------------------------
#------------------------------------------------------------------
# Endpoint 2: Ventas agrupadas por mes (corregido para MySQL)
# Esquema para la respuesta agrupada por mes
class MonthlySalesResponse(BaseModel):
    month: str  # Formato: YYYY-MM
    orders: List[OrderDetailsByUUIDResponse]

# Endpoint: Ventas agrupadas por el mes más reciente
@router.get("/ventas_por_mes_reciente", response_model=List[MonthlySalesResponse], status_code=status.HTTP_200_OK,
            description="Obtiene todas las órdenes de los últimos 30 días agrupadas por mes (YYYY-MM)")
async def ventas_por_mes_reciente(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve las órdenes detalladas agrupadas por el mes más reciente (últimos 30 días).
    """
    # Calcular la fecha de hace 30 días y la fecha de hoy (en CST)
    end = datetime.now(ZoneInfo("America/Chicago"))
    start = end - timedelta(days=30)

    # Consulta para obtener las órdenes con sus relaciones
    db_orders = (
        db.query(OrdersModel)
        .filter(
            OrdersModel.user_id == current_user.id_users,
            OrdersModel.date_time >= start,
            OrdersModel.date_time <= end
        )
        .options(
            joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
            joinedload(OrdersModel.user).joinedload(User.user_info),
            joinedload(OrdersModel.table)
        )
        .execution_options(compiled_cache=None)  # Deshabilitar caché para evitar errores
        .all()
    )

    if not db_orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes en los últimos 30 días para este usuario")

    # Agrupar las órdenes por mes en Python
    monthly_orders = {}
    for db_order in db_orders:
        # Calcular el mes (YYYY-MM)
        month_key = db_order.date_time.strftime("%Y-%m")

        if month_key not in monthly_orders:
            monthly_orders[month_key] = []

        # Construir los detalles de los productos
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

        # Obtener el nombre del restaurante
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el número de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        )

        # Construir la respuesta para la orden
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
            metodo_pago=db_order.metodo_pago
        )
        monthly_orders[month_key].append(response)

    # Convertir a la respuesta final
    result = [
        MonthlySalesResponse(month=month, orders=orders)
        for month, orders in monthly_orders.items()
    ]

    # Ordenar por mes
    result.sort(key=lambda x: x.month)

    return result

#------------------------------------------------------------------
# Endpoint: Ventas agrupadas por semana

# Esquema para la respuesta agrupada por semana
class WeeklySalesResponse(BaseModel):
    week: str  # Formato: YYYY-W##
    orders: List[OrderDetailsByUUIDResponse]

# Endpoint: Ventas agrupadas por la semana más reciente
@router.get("/ventas_por_semana", response_model=List[WeeklySalesResponse], status_code=status.HTTP_200_OK,
            description="Obtiene todas las órdenes de los últimos 7 días agrupadas por semana (YYYY-W##)")
async def ventas_por_semana(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve las órdenes detalladas agrupadas por la semana más reciente (últimos 7 días).
    """
    # Calcular la fecha de hace 7 días y la fecha de hoy
    end = datetime.now()
    start = end - timedelta(days=7)

    # Consulta para obtener las órdenes con sus relaciones
    db_orders = (
        db.query(OrdersModel)
        .filter(
            OrdersModel.user_id == current_user.id_users,
            OrdersModel.date_time >= start,
            OrdersModel.date_time <= end
        )
        .options(
            joinedload(OrdersModel.order_details).joinedload(OrdersDetailsModel.product),
            joinedload(OrdersModel.user).joinedload(User.user_info),
            joinedload(OrdersModel.table)
        )
        .execution_options(compiled_cache=None)  # Deshabilitar caché para evitar el error
        .all()
    )

    if not db_orders:
        raise HTTPException(status_code=404, detail="No se encontraron órdenes en los últimos 7 días para este usuario")

    # Agrupar las órdenes por semana en Python
    weekly_orders = {}
    for db_order in db_orders:
        # Calcular la semana ISO (YYYY-W##)
        year, week, _ = db_order.date_time.isocalendar()
        week_key = f"{year}-W{week:02d}"

        if week_key not in weekly_orders:
            weekly_orders[week_key] = []

        # Construir los detalles de los productos
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

        # Obtener el nombre del restaurante
        restaurant_name = (
            db_order.user.user_info.nombre_restaurante
            if db_order.user.user_info and db_order.user.user_info.nombre_restaurante
            else "Sin nombre de restaurante"
        )

        # Obtener el número de mesa
        mesa_number = (
            db_order.table.number if db_order.table and db_order.table.number else "Sin número de mesa"
        )

        # Construir la respuesta para la orden
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
            metodo_pago=db_order.metodo_pago
        )
        weekly_orders[week_key].append(response)

    # Convertir a la respuesta final
    result = [
        WeeklySalesResponse(week=week, orders=orders)
        for week, orders in weekly_orders.items()
    ]

    # Ordenar por semana
    result.sort(key=lambda x: x.week)

    return result