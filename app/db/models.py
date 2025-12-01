from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum, DateTime, ForeignKey, Float, Boolean
import sqlalchemy as sa
from sqlalchemy.types import DECIMAL as Decimal  # 🛠️ Corrección
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from app.db.database import Base
from enum import Enum as PyEnum  # Renombramos Enum de Python a PyEnum
from sqlalchemy.ext.hybrid import hybrid_property
from app.schemas import PlanType
from app.enums import RoleEnum, RoleOrders, TablesEnum, PaymentMethodEnum, StatusEnum, PlanType, PaymentStatus, SubscriptionAmount, OrderStatusEnum
from datetime import datetime
import uuid
from sqlalchemy import UniqueConstraint


"""
User → Orders: Un usuario puede tener varios pedidos (user.orders), y cada pedido tiene un solo usuario (orders.user).
User → Payments: Un usuario puede realizar varios pagos (user.payments), y cada pago está asociado a un solo usuario (payments.user).
User → Tables: Un usuario puede estar asociado a varias mesas (user.tables), y cada mesa tiene un solo usuario (tables.user).
Orders → OrdersDetails: Un pedido puede tener muchos detalles de productos (orders.details), y cada detalle está asociado a un solo pedido (orders_details.order).
Orders → Payments: Un pedido puede tener varios pagos (orders.payments), y cada pago está asociado a un solo pedido (payments.order).
OrdersDetails → Products: Cada detalle de pedido se refiere a un producto (orders_details.product), y cada producto puede estar en varios detalles de pedido (products.details).
"""
# RoleEnum es una clase que hereda de Enum de Python y de str de Python

# class  RoleEnum(str, PyEnum): 
#     admin = "admin"
#     user = "user"
#     client = "client"
# # RoleOrders es una clase que hereda de Enum de Python y de str de Python
# class RoleOrders(str, PyEnum):
#     Libre = "Libre"
#     Ocupado = "Ocupado"
# # TablesEnum es una clase que hereda de Enum de Python y de str de Python
# class TablesEnum(str, PyEnum):
#     Libre = "Libre"
#     Ocupado = "Ocupado"

# class StatusEnum(str, PyEnum):
#     activo = "activo"
#     inactivo = "inactivo"


# class PaymentMethodEnum(str, PyEnum):   
#     efectivo = "efectivo"
#     tarjeta = "tarjeta"
#     pasarela = "pasarela"



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

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id_users"))  # Relacionamos con la tabla de usuarios
    #product_id = Column(Integer, ForeignKey("products.id_products"), nullable=False)  # Clave foránea a la tabla 'products'
    product_id = Column(Integer, ForeignKey("products.id_products", ondelete="CASCADE"), nullable=True)  # Permitir NULL con CASCADE

    user = relationship("User", back_populates="images")
    product = relationship("Products", back_populates="images")  # Relación con Products
    

# class Restaurante(Base):
#     __tablename__= "restaurante"
#     id_restaurante = Column(Integer, primary_key=True, autoincrement=True)
#     nombre_restaurante = Column(String(50), nullable=True)  # Ahora opcional
#     ciudad = Column(String(50), nullable=True)  # Ahora opcional
#     estado_provincia = Column(String(50), nullable=True)  # Ahora opcional
#     alcadia = Column(String(50), nullable=True)  # Ahora opcional
#     owner_id = Column(Integer, ForeignKey("users.id_users"), nullable=False)  # Clave foránea obligatoria
#     # Relaciones
#     users = relationship("User", back_populates="restaurante", foreign_keys=lambda: [User.restaurante_id])
#     products = relationship("Products", back_populates="restaurante")
#     #categorias = relationship("Categoria", back_populates="restaurante")
#     owner = relationship("User", back_populates="restaurantes_propios", foreign_keys=[owner_id])

#alembic revision --autogenerate -m "Se modifica tables y se añade tables_details"

class User(Base):
    __tablename__ = "users"
    id_users = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=False, nullable = False)
    email = Column(String(50), unique=True, nullable = False)
    password = Column(String(255),  nullable = False)
    rol = Column(SQLAlchemyEnum(RoleEnum), nullable=False, default=RoleEnum.admin)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Campo para la fecha de creación
    #uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    #restaurante_id = Column(Integer, ForeignKey("restaurante.id_restaurante"), nullable=True)  # Nueva clave foránea, opcional
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    # Relaciones
    orders = relationship("Orders", back_populates="user")
    payments = relationship("Payments", back_populates="user")
    tables = relationship("Tables", back_populates="user")
    products = relationship("Products", back_populates="owner")  # Relación inversa
    images = relationship("Image", back_populates="user")
    #Nueva relación con UserInfo
    user_info = relationship("UserInfo", back_populates="user", uselist=False)  # uselist=False asegura relación 1:1
    # Relación con Restaurante como empleado (un usuario pertenece a un restaurante)
    #restaurante = relationship("Restaurante", back_populates="users", foreign_keys=[restaurante_id])
    # Relación con Restaurante como propietario (un usuario puede ser dueño de varios restaurantes)
    #restaurantes_propios = relationship("Restaurante", back_populates="owner", foreign_keys=[Restaurante.owner_id])
    order_analytics = relationship("OrderAnalytics", back_populates="user")
    table_details = relationship("TableDetails", back_populates="user")


    
class ImageUser(Base):
    __tablename__ = "image_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    user_info_id = Column(Integer, ForeignKey("user_info.id_user_info"), nullable=False, unique=True)  # Relación 1:1

    # Relación inversa
    user_info = relationship("UserInfo", back_populates="image_user")

class UserInfo(Base):
    __tablename__ = "user_info"
    id_user_info = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=True)
    #apellido = Column(String(50), nullable=True)
    email = Column(String(50), nullable=True)
    telefono = Column(String(50), nullable=True)
    direccion = Column(String(50), nullable=True)
    codigo_postal = Column(Integer, nullable=True)
    ciudad = Column(String(50), nullable=True)
    alcaldia = Column(String(50), nullable=True)
    nombre_restaurante = Column(String(50), nullable=True)
    whatsapp = Column(String(50), nullable=True)  # Nuevo campo para WhatsApp
    horario = Column(String(50), nullable=True)  # Nuevo campo para horario
    codigo_confirmacion = Column(String(4), nullable=True)  # Nueva columna

    # Relaciones
    # Clave foránea a la tabla 'users'
    user_id = Column(Integer, ForeignKey("users.id_users"), nullable=False, unique=True)  # unique=True asegura relación 1:1
    user_uuid = Column(String(50), nullable=True, unique=True)
    
    # Relación inversa con User
    user = relationship("User", back_populates="user_info")
    image_user = relationship("ImageUser", back_populates="user_info", uselist=False)  # Relación 1:1





# Orders es una clase que hereda de Base de SQLAlchemy
# Orders es una clase que representa la tabla orders de la base de datos
# Orders tiene los siguientes campos:
class Orders(Base):
    __tablename__ = "orders"
    id_orders = Column(Integer, primary_key=True, autoincrement=True)
    mesa_id = Column(Integer, ForeignKey("tables.id_tables"))  # Clave foránea a la tabla 'tables'
    state = Column(SQLAlchemyEnum(RoleOrders), nullable=False)
    order_status = Column(String(20), SQLAlchemyEnum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.Pendiente)  # Nuevo campo para el estado del pedido
    date_time = Column(DateTime)
    total = Column(Decimal(10, 2), default=0.00)
    orderscol = Column(String(50))
    product_name = Column(String(1500))
    user_id = Column(Integer, ForeignKey("users.id_users"))  # Agregar clave foránea
    order_uuid = Column(String(36), unique=False, nullable=False, default=lambda: str(uuid.uuid4()))  # Nuevo campo UUID
    metodo_pago = Column(SQLAlchemyEnum(PaymentMethodEnum), nullable=False, default=PaymentMethodEnum.efectivo)  # Nuevo campo para el método de pago
    ticket_number = Column(Integer, nullable=True)  # Cambiado a Integer
    descuento = Column(String(20), nullable=True, default="0")  # Nuevo campo para descuento

    #codigo_confirmacion = Column(String(4), nullable=False, server_default='0001')  # Valor por defecto temporal
    # Relaciones
    user = relationship("User", back_populates="orders") #
    #details = relationship("OrdersDetails", back_populates="order")
    #payments = relationship("Payments", back_populates="order")
    # Relación con la tabla `Tables`
    table = relationship("Tables", back_populates="orders")
    order_details = relationship("OrdersDetails", back_populates="order")
    
class UserConfirmationCode(Base):
    __tablename__ = "user_confirmation_codes"
    user_id = Column(Integer, ForeignKey("users.id_users"), primary_key=True)
    codigo_confirmacion = Column(String(4), nullable=False, server_default='0001')

class Tables(Base):
    __tablename__ = "tables"
    id_tables = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(Integer)
    capacity = Column(Integer)
    state = Column(SQLAlchemyEnum(TablesEnum), nullable=False)
    # Clave foránea a 'User'
    user_id = Column(Integer, ForeignKey("users.id_users"), nullable=False) 
    #subscription_amount = Column(SQLAlchemyEnum(SubscriptionAmount), nullable=False)  # Monto de la suscripción
    subscription_amount = Column(Integer, nullable=False)
    # --- ¡AGREGA ESTA LÍNEA! ---
    is_active = Column(Boolean, default=True, nullable=False, server_default=sa.text('1'))
    # Relaciones
    user = relationship("User", back_populates="tables")
    orders = relationship("Orders", back_populates="table")
    table_details = relationship("TableDetails", back_populates="table")


class TableDetails(Base):
    __tablename__ = "table_details"
    id_table_details = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("tables.id_tables"))
    #order_id = Column(Integer, ForeignKey("orders.id_orders"))
    user_id = Column(Integer, ForeignKey("users.id_users"), nullable=False)  # Clave foránea a la tabla 'users'
    table_number = Column(Integer, nullable=False)  # Número de la mesa (1, 2, ..., 26)
    estado = Column(SQLAlchemyEnum(TablesEnum), nullable=False, default=TablesEnum.Libre)  # Estado de la mesa
    cantidad_ventas_por_mesa = Column(Float, nullable=False, default=0.0)  # Cantidad de ventas por mesa
    # --- ¡ESTA ES LA COLUMNA QUE NECESITAS AGREGAR! ---
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relaciones
    table = relationship("Tables", back_populates="table_details")
    user = relationship("User", back_populates="table_details")
    

class Products(Base):
    __tablename__ = "products"
    id_products = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(1500))
    description = Column(String(500))
    price = Column(Decimal(10, 2))
    production_cost = Column(Decimal(10, 2), nullable=False, default=0.00)  # Nueva columna
    owner_id = Column(Integer, ForeignKey("users.id_users"))  # Nueva columna
    status = Column(SQLAlchemyEnum(StatusEnum), nullable=False, default=StatusEnum.activo)
    #restaurante_id = Column(Integer, ForeignKey("restaurante.id_restaurante"), nullable=True)  # Nueva clave foránea
    category_id = Column(Integer, ForeignKey("categoria.id_categoria"), nullable=False)  # Clave foránea a la tabla 'categoria'
    
    # Relaciones
    category = relationship("Categoria", back_populates="productos")
    owner = relationship("User", back_populates="products")  # Relación inversa
    order_details = relationship("OrdersDetails", back_populates="product")
    #images = relationship("Image", back_populates="product")  # Relación inversa
    images = relationship("Image", back_populates="product", cascade="all, delete-orphan")  # Añadir cascade
    #restaurante = relationship("Restaurante", back_populates="products")  # Relación inversa

    @hybrid_property
    def nombre_categoria(self):
        """Obtiene el nombre de la categoría desde la relación con Categoria."""
        return self.category.nombre_categoria


class OrdersDetails(Base):
    __tablename__ = "orders_details"
    id_orders_details = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id_orders"))
    product_id = Column(Integer, ForeignKey("products.id_products"))
    quantity = Column(Integer)
    unit_price = Column(Decimal(10, 2))  
    subtotal = Column(Decimal(10, 2))
    order_detail_status = Column(SQLAlchemyEnum(OrderStatusEnum), default=OrderStatusEnum.Pendiente)  # Nueva columna para estatus 
    #costo_producion = Column(Decimal(10, 2), nullable=False, default=0.00)  # Nueva columna
    utilidades = Column(Decimal(10, 2), nullable=True)  # Nueva columna para utilidades
    descuento_details = Column(String(20), nullable=True, default="0")  # Nuevo campo para descuento
    
    # Relaciones
      # Relaciones
    order = relationship("Orders", back_populates="order_details")
    product = relationship("Products", back_populates="order_details")


class Payments(Base):
    __tablename__ = "payments"
    id_payments = Column(Integer, primary_key=True, autoincrement=True)
    #order_id = Column(Integer, ForeignKey("orders.id_orders"))
    payment_method = Column(SQLAlchemyEnum(PaymentMethodEnum), nullable=False)
    amount = Column(Decimal(10, 2))
    date = Column(DateTime)
    subscription_end_date = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id_users"))  # Clave foránea a la tabla 'users'
    subscription_id = Column(String(255), nullable=True)  # Nuevo campo para el ID de la suscripción
    #plan = Column(SQLAlchemyEnum(PlanType), nullable=False)  # Nuevo campo para el plan
    plan = Column(SQLAlchemyEnum(PlanType, values_callable=lambda x: [e.value for e in x]), nullable=False)  # Nuevo campo para el plan, con valores de Enum
    status = Column(SQLAlchemyEnum(PaymentStatus), default=PaymentStatus.PENDING)
    checkout_session_id = Column(String(255), nullable=True)  # Nueva columna para el ID de la sesión de pago de Stripe
    email = Column(String(255), nullable=True)
    mercado_pago_preference_id = Column(String(255), nullable=True)
    mercado_pago_customer_id = Column(String(255), nullable=True)  # Nuevo campo
    mercado_pago_payment_id = Column(String(255), nullable=True)  # Nuevo campo
    mercado_pago_preapproval_id = Column(String(255), nullable=True)  # Nuevo campo
    checkout_url = Column(String(255), nullable=True)  # Nuevo campo para el enlace

    # Relaciones
    #order = relationship("Orders", back_populates="payments")
    user = relationship("User", back_populates="payments")

class Categoria(Base):
    __tablename__ = "categoria"
    id_categoria = Column(Integer, primary_key=True, autoincrement=True)
    nombre_categoria = Column(String(50), unique=True, nullable=False)
    descripcion_categoria = Column(String(255), nullable=False)
    status = Column(String(10), default="activo")
    #restaurante_id = Column(Integer, ForeignKey("restaurante.id_restaurante"), nullable=False)  # Nueva clav
    # Relación con productos
    productos = relationship("Products", back_populates="category")
    #restaurante = relationship("Restaurante", back_populates="categorias")
    owner_id = Column(Integer, ForeignKey("users.id_users"))  # Relación con el usuario
    


class OrderAnalytics(Base):
    __tablename__ = "order_analytics"

    id_analytics = Column(Integer, primary_key=True, autoincrement=True)
    period_start = Column(DateTime, nullable=False)  # Fecha de inicio del período (mes o semana)
    period_type = Column(String(10), nullable=False)  # "month" o "week"
    total_orders = Column(Integer, nullable=False)  # Número total de órdenes
    total_revenue = Column(Float,nullable=False)  # Suma del total de las órdenes
    total_products_sold = Column(Integer, nullable=False)  # Cantidad total de productos vendidos
    user_id = Column(Integer, ForeignKey("users.id_users"), nullable=False)  # Relación con el usuario

    # Relación inversa
    user = relationship("User", back_populates="order_analytics")


class Menucolors(Base):
    __tablename__ = "Menucolors"

    # Columna 1: El ID del usuario (Es Clave Primaria y Foránea a la vez)
    user_id = Column(Integer, ForeignKey("users.id_users"), primary_key=True)
    
    # Columna 2: El color
    color = Column(String(20), nullable=False) # Ej: "#000000"

    # Relación
    user = relationship("User")