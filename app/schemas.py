
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from decimal import Decimal
from typing import List, Union
from app.db.models import RoleEnum, RoleOrders, TablesEnum, CategoryEnum, PaymentMethodEnum
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


# EL cliente ingresara la categoria con un input el cual sera registrada
#en la base de datos, ver desde el front y actualizar en la abse de datos
class CategoryEnum(str, Enum):
    input = "activo"
    output = "inactivo"


#Para el metodo de pago
#La enumeración es una lista de valores que se pueden asignar a una variable.
class PaymentMethodEnum(str, Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"
  

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

# Esquema para mostrar un usuario (sin password, para GET)
class ShowUser(BaseModel):
    id_users: int| None = None
    name: str 
    email: str | None = None
    rol: RoleEnum 

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
    class Config:
        from_attributes = True

#esquema de las mesas donde tenemos state que es una enumeracion
#la cual nos permite identificar si la mesa esta libre u ocupada
#se inserta el id de la mesa, el numero y la capacidad
class Tables(BaseModel):
    #id_tables:int
    number:int
    capacity:int
    state:TablesEnum
    class Config:
        from_attributes = True

#Esquema de los productos 
class Products(BaseModel):
    #id_products:int
    name:str
    description:str
    price:Decimal
    stock:int 
    category:CategoryEnum  
    owner_id: int | None = None  # Añadir owner_id 
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
    unit_price:Decimal
    subtotal:Decimal
    class Config:
        from_attributes = True


#Esquema de los pagos
#Se inserta el id del pago, el id de la orden, el metodo de pago, 
# la cantidad y la fecha
class Payments(BaseModel):
    id_payments:int
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