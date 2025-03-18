from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum, DateTime, ForeignKey
from sqlalchemy.types import DECIMAL as Decimal  # 🛠️ Corrección
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from app.db.database import Base
from enum import Enum as PyEnum  # Renombramos Enum de Python a PyEnum


"""
User → Orders: Un usuario puede tener varios pedidos (user.orders), y cada pedido tiene un solo usuario (orders.user).
User → Payments: Un usuario puede realizar varios pagos (user.payments), y cada pago está asociado a un solo usuario (payments.user).
User → Tables: Un usuario puede estar asociado a varias mesas (user.tables), y cada mesa tiene un solo usuario (tables.user).
Orders → OrdersDetails: Un pedido puede tener muchos detalles de productos (orders.details), y cada detalle está asociado a un solo pedido (orders_details.order).
Orders → Payments: Un pedido puede tener varios pagos (orders.payments), y cada pago está asociado a un solo pedido (payments.order).
OrdersDetails → Products: Cada detalle de pedido se refiere a un producto (orders_details.product), y cada producto puede estar en varios detalles de pedido (products.details).
"""
# RoleEnum es una clase que hereda de Enum de Python y de str de Python

class  RoleEnum(str, PyEnum): 
    admin = "admin"
    user = "user"
    client = "client"
# RoleOrders es una clase que hereda de Enum de Python y de str de Python
class RoleOrders(str, PyEnum):
    Libre = "Libre"
    Ocupado = "Ocupado"
# TablesEnum es una clase que hereda de Enum de Python y de str de Python
class TablesEnum(str, PyEnum):
    Libre = "Libre"
    Ocupado = "Ocupado"

class CategoryEnum(str, PyEnum):
    input = "input"
    output = "output"

class PaymentMethodEnum(str, PyEnum):   
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"

# User es una clase que hereda de Base de SQLAlchemy
# Base es una clase que representa la base de datos
# User es una clase que representa la tabla users de la base de datos
# User tiene los siguientes campos:
# id_users, name, email, password, rol
# id_users es un entero que es la clave primaria de la tabla
# name es una cadena de texto que representa el nombre del usuario
# email es una cadena de texto que representa el correo electrónico del usuario
# password es una cadena de texto que representa la contraseña del usuario
# rol es una enumeración que representa el rol del usuario
# El rol del usuario puede ser "admin
# user" o "client"
# User tiene una relación con la tabla orders
# User tiene una relación con la tabla orders_details
# User tiene una relación con la tabla payments
# User tiene una relación con la tabla tables
# User tiene una relación con la tabla products
class User(Base):
    __tablename__ = "users"
    id_users = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable = False)
    email = Column(String(50), unique=True, nullable = False)
    password = Column(String(255),  nullable = False)
    rol = Column(SQLAlchemyEnum(RoleEnum), nullable=False, default=RoleEnum.admin)
    # Relaciones
    orders = relationship("Orders", back_populates="user")
    payments = relationship("Payments", back_populates="user")
    tables = relationship("Tables", back_populates="user")


# Orders es una clase que hereda de Base de SQLAlchemy
# Orders es una clase que representa la tabla orders de la base de datos
# Orders tiene los siguientes campos:
class Orders(Base):
    __tablename__ = "orders"
    id_orders = Column(Integer, primary_key=True, autoincrement=True)
    mesa_id = Column(Integer, ForeignKey("tables.id_tables"))  # Clave foránea a la tabla 'tables'
    state = Column(SQLAlchemyEnum(RoleOrders), nullable=False)
    date_time = Column(DateTime)
    total = Column(Decimal)
    orderscol = Column(String(50))
    user_id = Column(Integer, ForeignKey("users.id_users"))  # Agregar clave foránea
    # Relaciones
    user = relationship("User", back_populates="orders") #
    details = relationship("OrdersDetails", back_populates="order")
    payments = relationship("Payments", back_populates="order")
    # Relación con la tabla `Tables`
    table = relationship("Tables", back_populates="orders")

class Tables(Base):
    __tablename__ = "tables"
    id_tables = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(Integer)
    capacity = Column(Integer)
    state = Column(SQLAlchemyEnum(TablesEnum), nullable=False)
    # Clave foránea a 'User'
    user_id = Column(Integer, ForeignKey("users.id_users")) 

    # Relaciones
    user = relationship("User", back_populates="tables")
    orders = relationship("Orders", back_populates="table")
    

class Products(Base):
    __tablename__ = "products"
    id_products = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50))
    description = Column(String(50))
    price = Column(Decimal(10, 2))
    stock = Column(Integer)
    category = Column(SQLAlchemyEnum(CategoryEnum), nullable=False)
    # Relaciones
    details = relationship("OrdersDetails", back_populates="product")


class OrdersDetails(Base):
    __tablename__ = "orders_details"
    id_orders_details = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id_orders"))
    product_id = Column(Integer, ForeignKey("products.id_products"))
    quantity = Column(Integer)
    unit_price = Column(Decimal(10, 2))  
    subtotal = Column(Decimal(10, 2))
      # Relaciones
    order = relationship("Orders", back_populates="details")
    product = relationship("Products", back_populates="details")


class Payments(Base):
    __tablename__ = "payments"
    id_payments = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id_orders"))
    payment_method = Column(SQLAlchemyEnum(PaymentMethodEnum), nullable=False)
    amount = Column(Decimal(10, 2))
    date = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id_users"))  # Clave foránea a la tabla 'users'

    # Relaciones
    order = relationship("Orders", back_populates="payments")
    user = relationship("User", back_populates="payments")


