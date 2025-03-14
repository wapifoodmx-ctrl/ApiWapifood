from fastapi import FastAPI, HTTPException
import uvicorn
from app.routers import user, tables, products, orders, payments
from app.db.database import Base, engine


def creeate_tables():
    Base.metadata.create_all(bind=engine)
creeate_tables()
#Definimos la enumeracion para el rol de la comanda
#Y la insertamos en la clase siguiente para reconocer el rol
#get para solicitar datos 
#post para enviar datos
#put para actualizar datos
#delete para eliminar datos
app = FastAPI() 
app.include_router(user.router)
# Incluir los routers con prefijos específicos
app.include_router(tables.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)

if __name__ == "__main__":
    uvicorn.run("main:app", port = 8000, reload=True)


