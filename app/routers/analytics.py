from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.db.models import Orders, Payments, User, RoleEnum
from app.oauth import get_current_user
from app.db.database import get_db
from typing import Optional
from app.db.models import Restaurante
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


@router.get("/dashboard", response_model=AnalyticsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene métricas clave para el dashboard del restaurante.
    """
    # Definir períodos de tiempo
    today = datetime.now()
    start_of_current_week = today - timedelta(days=today.weekday(), hours=today.hour, minutes=today.minute, seconds=today.second, microseconds=today.microsecond)
    start_of_previous_week = start_of_current_week - timedelta(days=7)
    end_of_previous_week = start_of_current_week - timedelta(seconds=1)

    # Calcular el número de días en cada período
    days_in_current_period = (today - start_of_current_week).days + 1  # +1 para incluir el día actual
    days_in_previous_period = 7  # Semana pasada siempre tiene 7 días

    # Obtener el restaurante_id del usuario autenticado
    restaurante = (
        db.query(Restaurante)
        .filter(
            (Restaurante.owner_id == current_user.id_users) |  # Propietario
            (Restaurante.id_restaurante == current_user.restaurante_id)  # Empleado
        )
        .first()
    )

    if not restaurante:
        raise HTTPException(status_code=403, detail="No tienes restaurantes asociados para ver métricas")

    restaurante_id = restaurante.id_restaurante

    # 1. Ventas totales (usando Payments para mayor precisión)
    total_sales_current = (
        db.query(func.sum(Payments.amount))
        .join(Orders, Orders.id_orders == Payments.order_id)
        .filter(
            Orders.date_time >= start_of_current_week,
            Orders.date_time <= today,
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.restaurante_id == restaurante_id)
            )
        )
        .scalar() or 0.0
    )

    total_sales_previous = (
        db.query(func.sum(Payments.amount))
        .join(Orders, Orders.id_orders == Payments.order_id)
        .filter(
            Orders.date_time >= start_of_previous_week,
            Orders.date_time <= end_of_previous_week,
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.restaurante_id == restaurante_id)
            )
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
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.restaurante_id == restaurante_id)
            )
        )
        .scalar() or 0
    )

    total_orders_previous = (
        db.query(func.count(Orders.id_orders))
        .filter(
            Orders.date_time >= start_of_previous_week,
            Orders.date_time <= end_of_previous_week,
            Orders.user_id.in_(
                db.query(User.id_users).filter(User.restaurante_id == restaurante_id)
            )
        )
        .scalar() or 0
    )

    total_orders_change = calculate_percentage_change(total_orders_current, total_orders_previous)

    # 3. Clientes nuevos (usuarios con rol 'client' registrados esta semana)
    new_customers_current = (
        db.query(func.count(User.id_users))
        .filter(
            User.rol == RoleEnum.client,
            User.restaurante_id == restaurante_id,
            User.id_users.in_(
                db.query(Orders.user_id)
                .filter(Orders.date_time >= start_of_current_week, Orders.date_time <= today)
            )
        )
        .scalar() or 0
    )

    new_customers_previous = (
        db.query(func.count(User.id_users))
        .filter(
            User.rol == RoleEnum.client,
            User.restaurante_id == restaurante_id,
            User.id_users.in_(
                db.query(Orders.user_id)
                .filter(Orders.date_time >= start_of_previous_week, Orders.date_time <= end_of_previous_week)
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