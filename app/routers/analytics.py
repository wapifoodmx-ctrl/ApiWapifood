from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.db.models import Orders, Payments, User, RoleEnum, OrderAnalytics, OrdersDetails
from app.oauth import get_current_user
from app.db.database import get_db
from dateutil.relativedelta import relativedelta
from typing import Optional
#from app.db.models import Restaurante
from app.schemas import Metric, AnalyticsResponse, Orders as VentasSchema, VentasBasicSchema


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