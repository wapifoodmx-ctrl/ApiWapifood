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
from app.schemas import Metric, AnalyticsResponse


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

@router.get("/dashboard", response_model=AnalyticsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene métricas clave para el dashboard del usuario autenticado usando Orders.
    """
    # Definir períodos de tiempo
    today = datetime.now()
    start_of_current_week = today - timedelta(days=today.weekday(), hours=today.hour, minutes=today.minute, seconds=today.second, microseconds=today.microsecond)
    start_of_previous_week = start_of_current_week - timedelta(days=7)
    end_of_previous_week = start_of_current_week - timedelta(seconds=1)

    # Calcular el número de días en cada período
    days_in_current_period = (today - start_of_current_week).days + 1  # +1 para incluir el día actual
    days_in_previous_period = 7  # Semana pasada siempre tiene 7 días

    # 1. Ventas totales (usando Orders.total)
    total_sales_current = (
        db.query(func.sum(Orders.total))
        .filter(
            Orders.date_time >= start_of_current_week,
            Orders.date_time <= today,
            Orders.user_id == current_user.id_users
        )
        .scalar() or 0.0
    )

    total_sales_previous = (
        db.query(func.sum(Orders.total))
        .filter(
            Orders.date_time >= start_of_previous_week,
            Orders.date_time <= end_of_previous_week,
            Orders.user_id == current_user.id_users
        )
        .scalar() or 0.0
    )

    total_sales_change = calculate_percentage_change(total_sales_current, total_sales_previous)

    # 2. Pedidos totales (número de pedidos)
    total_orders_current = (
        db.query(func.count(Orders.id_orders))
        .filter(
            Orders.date_time >= start_of_current_week,
            Orders.date_time <= today,
            Orders.user_id == current_user.id_users
        )
        .scalar() or 0
    )

    total_orders_previous = (
        db.query(func.count(Orders.id_orders))
        .filter(
            Orders.date_time >= start_of_previous_week,
            Orders.date_time <= end_of_previous_week,
            Orders.user_id == current_user.id_users
        )
        .scalar() or 0
    )

    total_orders_change = calculate_percentage_change(total_orders_current, total_orders_previous)

    # 3. Clientes nuevos (usuarios con rol 'client' que hicieron pedidos esta semana)
    new_customers_current = (
        db.query(func.count(Orders.user_id.distinct()))
        .filter(
            Orders.date_time >= start_of_current_week,
            Orders.date_time <= today,
            Orders.user_id == current_user.id_users,
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.rol == RoleEnum.client)
            )
        )
        .scalar() or 0
    )

    new_customers_previous = (
        db.query(func.count(Orders.user_id.distinct()))
        .filter(
            Orders.date_time >= start_of_previous_week,
            Orders.date_time <= end_of_previous_week,
            Orders.user_id == current_user.id_users,
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.rol == RoleEnum.client)
            )
        )
        .scalar() or 0
    )

    new_customers_change = calculate_percentage_change(new_customers_current, new_customers_previous)

    # 4. Ventas promedio por día (ventas totales / número de días)
    average_daily_sales_current = (total_sales_current / days_in_current_period) if days_in_current_period > 0 else 0.0
    average_daily_sales_previous = (total_sales_previous / days_in_previous_period) if days_in_previous_period > 0 else 0.0
    average_daily_sales_change = calculate_percentage_change(average_daily_sales_current, average_daily_sales_previous)

    # Construir la respuesta
    return AnalyticsResponse(
        total_sales=Metric(
            value=float(total_sales_current),
            change=total_sales_change,
            change_label="vs la semana pasada"
        ),
        total_orders=Metric(
            value=float(total_orders_current),
            change=total_orders_change,
            change_label="vs la semana pasada"
        ),
        new_customers=Metric(
            value=float(new_customers_current),
            change=new_customers_change,
            change_label="vs la semana pasada"
        ),
        average_daily_sales=Metric(
            value=float(average_daily_sales_current),
            change=average_daily_sales_change,
            change_label="vs la semana pasada"
        )
    )

# -------------------------------------------------------------------------
#-----------------------------------------------------------------------


@router.post("/generate-analytics")
async def generate_analytics(
    period_type: str,  # "month" o "week"
    start_date: str,   # Formato: "YYYY-MM-DD", por ejemplo, "2025-01-01"
    end_date: str,     # Formato: "YYYY-MM-DD", por ejemplo, "2025-05-20"
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
            total_revenue=float(total_revenue),  # Convertir Decimal a float
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
    return {"message": f"Datos analíticos generados para {period_type} desde {start_date} hasta {end_date}"}


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