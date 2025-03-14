from fastapi import FastAPI, HTTPException
import uvicorn
<<<<<<< HEAD
from app.routers import user, tables, products, orders, payments
from app.db.database import Base, engine


def creeate_tables():
    Base.metadata.create_all(bind=engine)
creeate_tables()
#Definimos la enumeracion para el rol de la comanda
#Y la insertamos en la clase siguiente para reconocer el rol
=======
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from decimal import Decimal
from typing import List
#Definimos la enumeracion para el rol de la comanda
#Y la insertamos en la clase siguiente para reconocer el rol


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

# EL cliente ingresara la categoria con un input el cual sera registrada
#en la base de datos, ver desde el front y actualizar en la abse de datos
class CategoryEnum(str, Enum):
    input = "input"
    output = "output"


#Clases de enum para las mesas identificar ocupado y libre 
class TablesEnum(str, Enum):
    Libre ="Libre"
    Ocupado ="Ocupado"

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
    id_users: int
    name: str
    email: str
    password: str
    rol: RoleEnum  

class UserId(BaseModel):
    id_user:int

#class Orders(BaseModel):
class Orders(BaseModel):
    id_orders: int
    mesa_id: int
    state:RoleOrders
    date_time:datetime
    total:Decimal
    orderscol:str

#esquema de las mesas donde tenemos state que es una enumeracion
#la cual nos permite identificar si la mesa esta libre u ocupada
#se inserta el id de la mesa, el numero y la capacidad
class Tables(BaseModel):
    id_tables:int
    number:int
    capacity:int
    state:TablesEnum


#Esquema de los productos 
class Products(BaseModel):
    id_products:int
    name:str
    description:str
    price:Decimal
    stock:int 
    category:CategoryEnum  
#Esquema de los detalles de las ordenes
#Se inserta el id de la orden, el id del producto, la cantidad, el precio unitario
#y el subtotal
class OrdersDetails(BaseModel):
    id_orders_details:int
    order_id:int
    product_id:int
    quantity:int
    unit_price:Decimal
    subtotal:Decimal


class PaymentMethodEnum(str, Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"

#Esquema de los pagos
#Se inserta el id del pago, el id de la orden, el metodo de pago, 
# la cantidad y la fecha
class Payments(BaseModel):
    id_payments:int
    order_id:int
    payment_method:PaymentMethodEnum
    amount:Decimal
    date_time:datetime

#Se crean las listas de los usuarios, ordenes, mesas, productos, detalles de ordenes y pagos
#Para poder almacenar los datos temporales en la base de datos de la memoria
usuarios: List[User] = []
orders: List[Orders] = []
tables: List[Tables] = []
products: List[Products] = []
orders_details: List[OrdersDetails] = []
payments: List[Payments] = []

app = FastAPI()
usuarios = []

>>>>>>> 815fc3b68e8535623b8f64cba5a04034e0afbfac
#get para solicitar datos 
#post para enviar datos
#put para actualizar datos
#delete para eliminar datos
<<<<<<< HEAD
app = FastAPI() 
app.include_router(user.router)
# Incluir los routers con prefijos específicos
app.include_router(tables.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)
=======

@app.get("/ruta1") #OBtenemos el mensaje de Hola mundo 
def ruta1():
    return {"mensaje": "Hola mundo"}

@app.get("/user") #Del diccioanrio que creamos se guardan los ususaarios creados 
def obtener_usuarios():
    return usuarios

@app.post("/crear_usuario") #AL crear los usuarios nos muestra un mensaje 
def crear_usuario(user:User):
    usuario = user.dict()
    usuarios.append(usuario)
    return {"mensaje": "Usuario creado exitosamente"}

@app.post('/user/{user_id}') #Post para obtener el usuario apartir del id 
def obtener_usuario(user_id:int):
    for user in usuarios:
        if user["id_users"] == user_id:
            return {"usuario":user}
    return {"mensaje": "Usuario no encontrado"}


@app.post('/obtener_usuario2') #Obtenemos el usuario apartir del id
def Obtener_usuario(user_id:UserId):
    for user in usuarios:
        if user["id_users"] == user_id.id_user:
            return {"usuario":user}
    return {"mensaje": "Usuario no encontrado"}

@app.delete('/user{user_id}') #Eliminamos el usuario apartir del id
def eliminar_usuario(user_id:int):
    for index, user in enumerate(usuarios):#Se recorre el indice y el usuario
        if user["id_users"] == user_id:
            usuarios.pop(index) #el pop hace que se elimine el usuario en el indice
            return {"mensaje": "Usuario eliminado exitosamente"}
    return {"mensaje": "Usuario no encontrado"}


@app.put('/user{user_id}') #Actualizamos el usuario apartir del id
def actualizar_usuario(user_id:int, updateUser:User): #Actualizamos el usuario apartir del id
    for index, user in enumerate(usuarios):#Se recorre el indice y el usuario
        if user["id_users"] == user_id:#Si el usuario es igual al id del usuario
            usuarios[index]["id_user"] = updateUser.name.dict()["id_user"]
            usuarios[index]["name"] = updateUser.name.dict()["name"]
            usuarios[index]["email"] = updateUser.name.dict()["email"]
            usuarios[index]["password"] = updateUser.name.dict()["password"]
            usuarios[index]["rol"] = updateUser.name.dict()["rol"]
            #Se actualiza el nombre
            return {"mensaje": "Usuario actualizado exitosamente"}
    return {"mensaje": "Usuario no encontrado"}

@app.get("/tables", response_model=List[Tables]) #Obtenemos las mesas
def obtener_las_mesas():
    return tables

@app.post("/tables", response_model=dict) #Creamos las mesas
def crear_mesa(table: Tables):
    tables.append(table)
    return {"mensaje": "Mesa creada exitosamente"}

@app.get("/orders", response_model=List[Orders])#Obtenemos las ordenes
def obtener_ordenes():
    return orders

@app.post("/orders", response_model=dict)#Creamos las ordenes
def creamos_ordenes(order: Orders):
    orders.append(order)
    return {"mensaje": "Orden creada exitosamente"}

@app.get("/products", response_model=List[Products])#Obtenemos los productos
def obtenemos_productos():
    return products

@app.post("/products", response_model=dict)#Creamos los productos
def creamos_producto(product: Products):
    products.append(product)
    return {"mensaje": "Producto creado exitosamente"}#Mensaje de producto creado exitosamente

@app.put("/tables/{table_id}")#Actualizamos las mesas
def actualizamos_mesa(table_id: int, table: Tables):#Actualizamos las mesas apartir del id de la mesa y la mesa 
    for index, t in enumerate(tables):
        if t.id_tables == table_id:
            tables[index] = table
            return {"mensaje": "Mesa actualizada"}
    raise HTTPException(status_code=404, detail="Mesa no encontrada")
>>>>>>> 815fc3b68e8535623b8f64cba5a04034e0afbfac

if __name__ == "__main__":
    uvicorn.run("main:app", port = 8000, reload=True)


