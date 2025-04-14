from pydantic import BaseModel, field_validator
from enum import Enum
from datetime import datetime
from decimal import Decimal
from typing import List, Union, Optional
from app.db.models import RoleEnum, RoleOrders, TablesEnum, PaymentMethodEnum
#Para el rol de los usuarios
#La enumeración es una lista de valores que se pueden asignar a una variable.
#En este caso, el rol puede ser "admin
#user" o "client".
#El modelo de datos se puede usar para validar y serializar datos.
#La enumeración es una lista de valores que se pueden asignar a una variable.
class RoleEnum(str, Enum):
    admin ="admin"
    user ="user"
    client ="client"

#Para el rol de las mesas 
#En este caso, el rol puede ser "admin
class RoleOrders(str, Enum):
    Libre ="Libre"
    Ocupado ="Ocupado"


#Clases de enum para las mesas identificar ocupado y libre 
class TablesEnum(str, Enum):
    Libre ="Libre"
    Ocupado ="Ocupado"


#Para el metodo de pago
#La enumeración es una lista de valores que se pueden asignar a una variable.
class PaymentMethodEnum(str, Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"

class StatusEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class PaymentMethodEnum(str, Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"




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

    class Config:
        from_attributes = True

class UserId(BaseModel):
    id_user:int 

class UserInfo(BaseModel):
    id_user_info: int | None = None
    nombre: str
    apellido: str
    email: str
    telefono: str
    direccion: str
    codigo_postal: int
    ciudad: str
    alcaldia: str
    user_id: int | None = None # Clave foránea que conecta con User

    class Config:
        from_attributes = True  # Para compatibilidad con SQLAlchemy
        
class UserWithInfo(BaseModel):
    user_info: UserInfo | None = None  # Relación opcional con UserInfo

    class Config:
        from_attributes = True

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
    #id_orders_details:int
    order_id:int
    product_id:int
    quantity:int
    #unit_price:Decimal
    #subtotal:Decimal
    class Config:
        from_attributes = True


#class Orders(BaseModel):
class Orders(BaseModel):
    #id_orders: int
    mesa_id: int
    state:RoleOrders
    date_time:datetime
    total:Decimal
    orderscol:str
    order_details: List[OrdersDetails]  # Agregar los detalles de la orden
    class Config:
        from_attributes = True


class OrdersResponse(BaseModel):
    id_orders: int
    #mesa_id: int
    state: RoleOrders
    date_time: datetime
    total: Decimal
    orderscol: str
    user_id: int
    order_details: List[OrdersDetails]

    class Config:
        from_attributes = True



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


# Esquema para crear un producto (con campos adicionales)
class ProductsCreate(BaseModel):
    name: str
    description: str
    price: Decimal
    category_id: int | None = None  # Cambié a int | None
    status: Optional[StatusEnum] = None
    #mesa_id: Optional[int] = 1  # Para el pedido
    quantity: Optional[int] = 1  # Para OrdersDetails

    class Config:
        from_attributes = True

#Esquema de los productos 
class Products(BaseModel):
    id_products:int | None = None
    name:str
    description:str
    price:Decimal
    category_id:int 
    status:StatusEnum | None = None
    image_url: str | None = None  # Nuevo campo para la URL de la imagen

    #owner_id: int | None = None  # Añadir owner_id 
    class Config:
        from_attributes = True


class ProductsPatch(BaseModel):  # Nuevo esquema para actualizaciones parciales
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    quantity: Optional[int] = None
    status: Optional[StatusEnum] = None

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

class ImageUserResponse(BaseModel):
    id: int | None = None
    file_name: str
    file_path: str
    user_info_id: int

    class Config:
        from_attributes = True


class UserInfoCreate(BaseModel):
    nombre: str
    apellido: str
    email: str
    telefono: str
    direccion: str
    codigo_postal: int
    ciudad: str
    alcaldia: str

    class Config:
        from_attributes = True

class UserInfoResponse(BaseModel):
    id_user_info: int | None = None
    nombre: str
    apellido: str
    email: str
    telefono: str
    direccion: str
    codigo_postal: int
    ciudad: str
    alcaldia: str
    user_id: int | None = None
    image_user: Optional[ImageUserResponse] = None  # Incluye la imagen si existe

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
    products: List[Products] | None = None  # Relación con Products

    class Config:
        from_attributes = True


class RestauranteCreate(BaseModel):
    nombre_restaurante: str
    ciudad: str
    estado_provincia: str
    alcadia: str

    class Config:
        from_attributes = True

class Restaurante(BaseModel):
    id_restaurante: int | None = None
    nombre_restaurante: str
    ciudad: str
    estado_provincia: str
    alcadia: str

    class Config:
        from_attributes = True