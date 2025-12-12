from pydantic import BaseModel, field_validator, computed_field, EmailStr, Field
from enum import Enum
from datetime import datetime
from decimal import Decimal
from typing import List, Union, Optional
#from app.db.models import RoleEnum, RoleOrders, TablesEnum, PaymentMethodEnum
from app.enums import RoleEnum, RoleOrders, TablesEnum, PaymentMethodEnum, StatusEnum, PlanType, OrderStatusEnum
#Para el rol de los usuarios
#La enumeración es una lista de valores que se pueden asignar a una variable.
#En este caso, el rol puede ser "admin
#user" o "client".
#El modelo de datos se puede usar para validar y serializar datos.
# #La enumeración es una lista de valores que se pueden asignar a una variable.
# class RoleEnum(str, Enum):
#     admin ="admin"
#     user ="user"
#     client ="client"

# #Para el rol de las mesas 
# #En este caso, el rol puede ser "admin
# class RoleOrders(str, Enum):
#     Libre ="Libre"
#     Ocupado ="Ocupado"


# #Clases de enum para las mesas identificar ocupado y libre 
# class TablesEnum(str, Enum):
#     Libre ="Libre"
#     Ocupado ="Ocupado"


# #Para el metodo de pago
# #La enumeración es una lista de valores que se pueden asignar a una variable.
# class PaymentMethodEnum(str, Enum):
#     efectivo = "efectivo"
#     tarjeta = "tarjeta"
#     pasarela = "pasarela"


# # Definir los tipos de planes disponibles como un Enum
# class PlanType(str, Enum):
#     BASICO = "basico"
#     PROFESIONAL = "profesional"
#     EMPRESARIAL = "empresarial"



# class StatusEnum(str, Enum):
#     activo = "activo"
#     inactivo = "inactivo"




#BAse model # A Pydantic model
#BaseModel es una clase de Pydantic que nos permite definir un modelo de datos
#que se puede usar para validar y serializar datos.
#En este caso, estamos definiendo un modelo de datos para un usuario que tiene
#un id, un nombre, un correo electrónico, una contraseña y un rol.
#El id es un entero, el nombre y el correo electrónico son cadenas de texto,
#la contraseña es una cadena de texto y el rol es una enumeración.
#La enumeración es una lista de valores que se pueden asignar a una variable.
#En este caso, el rol puede ser "admin
#user" o "client".
#El modelo de datos se puede usar para validar y serializar datos.
class User(BaseModel):
    id_users: int | None = None
    name: str
    email: str | None = None
    password: str 
    rol: RoleEnum  | None = None
    #restaurante_id: Optional[int] = None  # ID del restaurante asociado (opcional)

    class Config:
        from_attributes = True

class UserId(BaseModel):
    id_user:int 

class UserInfo(BaseModel):
    id_user_info: int | None = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    codigo_postal: Optional[int] = None
    ciudad: Optional[str] = None
    alcaldia: Optional[str] = None
    nombre_restaurante: Optional[str] = None  # Nombre del restaurante asociado
    user_id: int | None = None  # Clave foránea que conecta con User
    user_uuid: Optional[str] = None  # UUID del usuario (opcional)
    codigo_confirmacion: Optional[str] = None  # Añadir este campo

    class Config:
        from_attributes = True  # Para compatibilidad con SQLAlchemy
        

# Esquema para mostrar un usuario (sin password, para GET)
class ShowUser(BaseModel):
    id_users: int| None = None
    name: str 
    email: str | None = None
    rol: RoleEnum 

    class Config:
        from_attributes = True

#Esquema de los detalles de las ordenes
#Se inserta el id de la orden, el id del producto, la cantidad, el precio unitario
#y el subtotal
class OrdersDetails(BaseModel):
    id_orders_details:int | None = None
    order_id:int | None = None
    product_id:int
    quantity:int
    unit_price:Decimal
    subtotal:Decimal
    order_detail_status: OrderStatusEnum = OrderStatusEnum.Pendiente
    class Config:
        from_attributes = True

class OrdersDetailsSchema(BaseModel):
    id_orders_details: int | None = None
    order_id: int | None = None
    product_id: int
    quantity: int
    unit_price: Decimal  # Cambiar a Decimal para coincidir con OrdersDetails
    descuento_details: Optional[str] = "0"  # Nuevo campo para descuento por detalle
    subtotal: Decimal  # Cambiar a Decimal para coincidir con OrdersDetails
    order_detail_status: OrderStatusEnum = OrderStatusEnum.Pendiente  # Nuevo campo

    class Config:
        from_attributes = True


class Orders(BaseModel):
    id_orders: int | None = None
    state: RoleOrders
    order_status: OrderStatusEnum = OrderStatusEnum.Pendiente  # Nuevo campo para el estado de la orden
    date_time: datetime
    total: Decimal
    orderscol: str
    user_id: int
    product_name: str
    order_details: List[OrdersDetailsSchema]

    class Config:
        from_attributes = True

# Nuevo esquema para la respuesta de creación de órdenes
# class OrderCreateResponse(Orders):
#     mesa_id: Optional[int] = None  # ID de la mesa asignada
#     mesa_number: Optional[int] = None  # Número de la mesa asignada

#     class Config:
#         from_attributes = True

class OrderCreateResponse(BaseModel):
    id_orders: int | None = None
    state: RoleOrders
    order_status: OrderStatusEnum = OrderStatusEnum.Pendiente
    date_time: datetime
    descuento: Optional[str] = "0" 
    total: Decimal
    orderscol: str
    user_id: int
    product_name: str
    order_details: List[OrdersDetailsSchema]
    mesa_id: int  # ID de la mesa asignada
    mesa_number: int  | None = None # Número de la mesa asignada
    order_uuid: str  # Nuevo campo para el UUID único de la orden

    class Config:
        from_attributes = True


class OrdersResponse(BaseModel):
    id_orders: int | None = None
    state: RoleOrders
    order_status: OrderStatusEnum = OrderStatusEnum.Pendiente  # Nuevo campo
    date_time: datetime
    total: Decimal  # Cambiar a Decimal para coincidir con OrdersModel
    orderscol: str
    user_id: int | None = None
    order_uuid: str  # Nuevo campo para el UUID único de la orden
    product_name: str
    details: List[OrdersDetailsSchema]  # Cambiar a "details" para mantener consistencia

    class Config:
        from_attributes = True






# class ConfirmationCodeResponse(BaseModel):
#     code: str

#     class Config:
#         from_attributes = True

#esquema de las mesas donde tenemos state que es una enumeracion
#la cual nos permite identificar si la mesa esta libre u ocupada
#se inserta el id de la mesa, el numero y la capacidad
class Tables(BaseModel):
    #id_tables:int
    number:int
    capacity:int
    state:TablesEnum = "libre"
    class Config:
        from_attributes = True


class OrderDetailItem(BaseModel):
    id_orders_details: int | None = None  # Nuevo campo para id_orders_details
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    order_detail_status: OrderStatusEnum 

    class Config:
        from_attributes = True

class OrderDetailsByUUIDResponse(BaseModel):
    id_orders: int | None = None
    mesa_number: Optional[Union[str, int]]
    restaurant_name: str
    order_uuid: str
    date_time: datetime
    state: RoleOrders
    order_status: OrderStatusEnum
    products: List[OrderDetailItem]
    total: Decimal
    metodo_pago: PaymentMethodEnum
    ticket_number: Optional[int] = None  # Nuevo campo para ticket_number

    class Config:
        from_attributes = True


# Esquema para crear un producto (con campos adicionales)
class ProductsCreate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    category_id: int | None = None  # Cambié a int | None
    status: Optional[StatusEnum] = None
    #mesa_id: Optional[int] = 1  # Para el pedido
    quantity: Optional[int] = 1  # Para OrdersDetails

    class Config:
        from_attributes = True

class ImageResponse(BaseModel):
    file_name: str
    file_path: str

    @property
    def url(self):
        # Construye la URL completa (ajusta según tu configuración)
        return f"https://api.wapifood.com/static/uploads/{self.file_name}"
        
        #return f"http://192.168.1.69/static/uploads/{self.file_name}"

    class Config:
        orm_mode = True

class ProductsSchema(BaseModel):
    id_products: int
    name: str
    description: Optional[str]
    price: float
    status: str
    category_id: Optional[int]
    owner_id: int
    image_url: List[ImageResponse] = []  # Incluye las imágenes asociadas

    class Config:
        orm_mode = True

#Esquema de los productos 
class Products(BaseModel):
    id_products: int | None = None
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    category_id: int | None = None  # Cambié a int | None
    status: StatusEnum | None = None
    image_url: List[str] = []
    production_cost: Optional[Decimal] = None  # Nuevo campo para costo de producción
    nombre_categoria: Optional[str] = None  # Agregar el campo calculado


    class Config:
        from_attributes = True


class ProductsPatch(BaseModel):  # Nuevo esquema para actualizaciones parciales
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    quantity: Optional[int] = None
    status: Optional[StatusEnum] = None

class TopProduct(BaseModel):
    position: int
    name: str
    price: float
    units_sold: int
    subtotal: float

    class Config:
        from_attributes = True

#Esquema de los pagos
#Se inserta el id del pago, el id de la orden, el metodo de pago, 
# la cantidad y la fecha
class Payments(BaseModel):
    id_payments:int | None = None
    order_id:int
    payment_method:PaymentMethodEnum
    amount:Decimal
    date_time:datetime
    class Config:
        from_attributes = True

class Login(BaseModel):
    email: str 
    password: str
    class Config:
        from_attributes = True  # Para Pydantic V2


class TokenData(BaseModel):
    name: Union[str, None] = None
    username: str | None = None

# Nuevos esquemas para imágenes
class ImageCreate(BaseModel):
    file_name: str
    file_path: str | None = None
    user_id: int | None = None
    product_id: Optional[int] = None  # Hacer product_id opcional

    class Config:
        from_attributes = True

class ImageResponse(BaseModel):
    id: int | None = None
    file_name: str
    file_path: str | None = None
    user_id: int | None = None
    product_id: Optional[int] = None  # Hacer product_id opcional
    class Config:
        from_attributes = True

class ImageUserCreate(BaseModel):
    file_name: str
    file_path: str
    user_info_id: int | None = None

    class Config:
        from_attributes = True


import os


class ImageUserResponse(BaseModel):
    id: Optional[int] = None
    file_name: str
    file_path: str
    user_info_id: int

    @computed_field
    @property
    def url(self) -> str:
        base_url = os.getenv("BASE_URL", "https://api.wapifood.com")  # Alinear con products.py
        return f"{base_url}/static/uploads/{self.file_name}"

    class Config:
        from_attributes = True

        #https://api.wapifood.com
        #https://api.wapifood.com

# class ImageUserResponse(BaseModel):
#     id: int | None = None
#     file_name: str
#     file_path: str
#     user_info_id: int

#     class Config:
#         from_attributes = True


class UserInfoCreate(BaseModel):
    nombre: str | None = None 
    apellido: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    codigo_postal: int | None = None
    ciudad: str | None = None 
    alcaldia: str | None = None
    nombre_restaurante: str | None = None  # Nombre del restaurante asociado
    user_id: Optional[int] = None
    user_uuid: Optional[str] = None  # Correcto como str
    whatsapp: Optional[str] = None  # Nuevo campo para WhatsApp
    horario: Optional[str] = None
    image_user: Optional[ImageUserCreate] = None  # Nuevo campo para la imagen del usuario
    # Nuevo campo para el código de confirmación
    codigo_confirmacion: Optional[str] = None

    class Config:
        from_attributes = True

class UserInfoResponse(BaseModel):
    id_user_info: int | None = None
    nombre: Optional[str] = None
    #apellido: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    codigo_postal: Optional[int] = None
    ciudad: Optional[str] = None
    alcaldia: Optional[str] = None
    nombre_restaurante: Optional[str] = None  # Nombre del restaurante asociado
    whatsapp: Optional[str] = None  # Nuevo campo para WhatsApp
    horario: Optional[str] = None  # Nuevo campo para horario
    user_id: int | None = None
    user_uuid: Optional[str] = None  # Correctamente definido como str
    image_user: Optional[ImageUserResponse] = None
    codigo_confirmacion: Optional[str] = None

    class Config:
        orm_mode = True  # Nota: orm_mode es para Pydantic V1; en V2 es from_attributes


class UserWithInfo(BaseModel):
    id_users: int
    name: str
    email: Optional[str] = None
    rol: RoleEnum
    user_info: Optional[UserInfoResponse] = None  # Cambiado de UserInfo a UserInfoResponse

    class Config:
        from_attributes = True


class UserInfoByUUIDResponse(BaseModel):
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    nombre_restaurante: Optional[str] = None
    whatsapp: Optional[str] = None
    image: Optional[str] = None
    direccion: Optional[str] = None
    codigo_postal: Optional[int] = None
    ciudad: Optional[str] = None
    alcaldia: Optional[str] = None
    #codigo_confirmacion: Optional[str] = None
    horario: Optional[str] = None

    class Config:
        from_attributes = True
        

class CategoriaCreate(BaseModel):
    nombre_categoria: str
    descripcion_categoria: str # Cambié "description_categoria" a seguir tu convención
    status: StatusEnum | None = "activo"  # Por defecto "activo" si no se especifica

    class Config:
        from_attributes = True        

class Categoria(BaseModel):
    id_categoria:int | None = None
    nombre_categoria:str
    descripcion_categoria:str
    status:StatusEnum | None = None
    owner_id: int | None = None
    products: List[Products] | None = None  # Relación con Products

    class Config:
        from_attributes = True


class ProductInCategory(BaseModel):
    id_products: int | None = None
    name: str
    description: str
    price: Decimal
    category_id: int
    status: StatusEnum | None = None
    image_url: List[str] = []  # Lista de URLs de imágenes
    nombre_categoria: Optional[str] = None

    class Config:
        from_attributes = True

# Esquema para una categoría con sus productos
class CategoryWithProducts(BaseModel):
    nombre_categoria: str
    productos: List[ProductInCategory]

    class Config:
        from_attributes = True

# Esquema para categorías simples (solo id y nombre)
class CategoriaSimple(BaseModel):
    id_categoria: int
    nombre_categoria: str

    class Config:
        from_attributes = True


# class RestauranteBase(BaseModel):
#     nombre_restaurante: Optional[str] = None
#     ciudad: Optional[str] = None
#     estado_provincia: Optional[str] = None
#     alcadia: Optional[str] = None

# class RestauranteCreate(RestauranteBase):
#     pass  # Hereda los campos opcionales de RestauranteBase

# class RestauranteUpdate(RestauranteBase):
#     pass  # También hereda los campos opcionales

# class Restaurante(RestauranteBase):
#     id_restaurante: int
#     owner_id: int

#     class Config:
#         orm_mode = True

class OrderDetailCreate(BaseModel):
    product_id: int
    quantity: int

class OrdersCreate(BaseModel):
    details: List[OrderDetailCreate]
    mesa_id: int

    class Config:
        from_attributes = True

class OrderDetailResponse(BaseModel):
    #product_id: int
    quantity: int
    unit_price: float = 0.0
    subtotal: float
    descuento_details: Optional[str] = "0" 
    order_detail_status: OrderStatusEnum = OrderStatusEnum.Pendiente  # Nuevo campo

    class Config:
        orm_mode = True


class OrdersResponse(BaseModel):
    id_orders: int
    #mesa_id: int
    mesa_number: Optional[int] = None
    state: RoleOrders  # Cambiado de str a RoleOrders
    order_status: OrderStatusEnum = OrderStatusEnum.Pendiente
    date_time: datetime
    descuento: Optional[str] = "0"  # Nuevo campo
    total: Decimal  # Cambiado de float a Decimal para precisión
    orderscol: str
    user_id: Optional[int] = None
    order_uuid: str
    product_name: str = "Sin dato"
    details: List[OrderDetailResponse]

    class Config:
        orm_mode = True


class ProductUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    category_id: Optional[int] = None
    production_cost: Optional[Decimal] = None  # Nuevo campo para costo de producción



# Esquema para las métricas
class Metric(BaseModel):
    value: float  # Valor actual (puede ser un número o porcentaje)
    change: float  # Cambio porcentual respecto al período anterior
    change_label: str  # Etiqueta del cambio (por ejemplo, "vs la semana pasada")

class AnalyticsResponse(BaseModel):
    total_sales: Metric
    total_orders: Metric
    new_customers: Metric
    average_daily_sales: Metric 

class VentasBasicSchema(BaseModel):
    id_orders: int
    date: str | None
    value: float 



class Item(BaseModel):
    id: Optional[str] = None
    quantity: int
    price: int

class PaymentResponse(BaseModel):
    id_payments: int | None = None
    user_id: int 
    amount: Decimal 
    date: datetime
    status: str
    plan: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    checkout_session_id: str | None
    mercado_pago_customer_id: str | None = None
    mercado_pago_payment_id: str | None = None
    mercado_pago_preapproval_id: str | None = None
    checkout_url: str | None = None  # Nuevo campo para el enlace

    class Config:
        from_attributes = True

   

class PaymentRequest(BaseModel):
    items: List[Item]
    order_id: int  # Agregamos order_id para asociar el pago a un pedido

# Esquema para la solicitud de pago
class SubscriptionRequest(BaseModel):
    plan: PlanType
    card_token: Optional[str] = None
    #order_id: str

    class Config:
        from_attributes = True


class OrderFinalizeResponse(BaseModel):
    message: str
    order_id: int
    mesa_id: int
    order_status: OrderStatusEnum
    mesa_state: TablesEnum
    metodo_pago: PaymentMethodEnum | None = None  # Nuevo campo para metodo_pago
    ticket_number: Optional[int] = None  # Nuevo campo para ticket_number


    class Config:
        from_attributes = True


# Esquema mínimo para la respuesta
class ConfirmationCodeResponse(BaseModel):
    codigo_confirmacion: Optional[str]


#esquema respuesta utilidadesss
class UtilidadesResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    costo_producion: Decimal  # Nota: hay un typo aquí, debería ser "costo_produccion"
    Venta_total: Decimal
    utilidades: Decimal

    class Config:
        from_attributes = True


# Esquema para solicitud de restablecimiento de contraseña
class PasswordResetRequest(BaseModel):
    email: EmailStr

# Esquema para confirmación de restablecimiento de contraseña
class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# Esquema para respuesta de confirmación
class PasswordResetResponse(BaseModel):
    message: str



class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationResponse(BaseModel):
    token: str
    user_uuid: str
    message: str


# Schema para recibir datos (POST/PUT)
class MenucolorRequest(BaseModel):
    color: str

# Schema para responder (GET)
class MenucolorResponse(BaseModel):
    user_id: int
    color: str

    class Config:
        from_attributes = True

# 🆕 Schema para Actualizar Mesero
class WaiterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Nuevo nombre del mesero")
    access_code: Optional[str] = Field(None, min_length=6, max_length=6, pattern=r"^\d{6}$", description="Nuevo código de 6 dígitos")


# Schema para CREAR (Lo que envía el front)
class WaiterCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre del mesero")
    access_code: str = Field(..., pattern=r"^\d{6}$", description="Código de 6 dígitos numéricos")

# Schema para RESPONDER (Lo que devuelve la API)
class WaiterResponse(BaseModel):
    uuid: str
    name: str
    access_code: str # Opcional: podrías ocultarlo si quisieras seguridad extra

    class Config:
        from_attributes = True


# 🆕 Schema para el login de meseros
class WaiterLoginSchema(BaseModel):
    email: EmailStr = Field(..., description="Correo del Restaurante (Dueño)")
    access_code: str = Field(..., min_length=6, max_length=6, description="Código de 6 dígitos del mesero")


# 1. Esquema simple para el mesero
class WaiterInOrder(BaseModel):
    name: str
    uuid: str

# 2. Esquema simple para los detalles (productos)
class OrderDetailSimple(BaseModel):
    pass
# 3. ESQUEMA FINAL: Orden con Meseros
class OrderWithWaitersResponse(BaseModel):
    # state: str  <-- Eliminado
    # order_status: str <-- Eliminado
    # descuento: str <-- Eliminado
    # total: float <-- Eliminado
    # orderscol: Optional[str] <-- Eliminado
    order_uuid: str
    
    waiters: List[WaiterInOrder] = []
    details: List[OrderDetailSimple] = [] # Lista de detalles (ahora vacíos)

    class Config:
        from_attributes = True


class WaiterLimitResponse(BaseModel):
    plan_name: str
    max_waiters: int
    current_waiters: int
    remaining_slots: int