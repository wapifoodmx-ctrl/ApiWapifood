# app/repository/products.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Products, OrdersDetails
from app.schemas import TopProduct
from typing import List

def get_top_products(db: Session, user_id: int) -> List[TopProduct]:
    top_products_query = (
        db.query(
            Products.id_products,
            Products.name.label("name"),
            Products.price.label("price"),
            func.sum(OrdersDetails.quantity).label("units_sold"),
            func.sum(OrdersDetails.subtotal).label("subtotal")
        )
        .join(OrdersDetails, OrdersDetails.product_id == Products.id_products)
        .filter(Products.owner_id == user_id)
        .group_by(Products.id_products, Products.name, Products.price)
        .order_by(func.sum(OrdersDetails.subtotal).desc())
        .limit(6)
    )

    results = top_products_query.all()

    if not results:
        return []

    top_products = [
        TopProduct(
            position=index + 1,
            name=row.name,
            price=row.price,
            units_sold=row.units_sold,
            subtotal=row.subtotal
        )
        for index, row in enumerate(results)
    ]

    return top_products