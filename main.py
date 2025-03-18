from fastapi import FastAPI, HTTPException
import uvicorn
from app.routers import user, tables, products, orders, payments, auth
from app.db.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware



#def creeate_tables():
# Base.metadata.create_all(bind=engine)
#creeate_tables()
#Definimos la enumeracion para el rol de la comanda
#Y la insertamos en la clase siguiente para reconocer el rol
#get para solicitar datos 
#post para enviar datos
#put para actualizar datos
#delete para eliminar datos
app = FastAPI() 
app.include_router(user.router)
app.include_router(auth.router)
# Incluir los routers con prefijos específicos
app.include_router(tables.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)


if __name__ == "__main__":
    uvicorn.run("main:app", port = 8000, reload=True)


# Configuración de CORS
origins = [
    "http://localhost:3000",  # Origen de tu frontend
    "http://localhost:5173",  # Otro puerto común para Vite/React
    "http://127.0.0.1:3000",  # Variación del localhost
    # Agrega más orígenes según necesites
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Lista de orígenes permitidos
    allow_credentials=True,  # Permitir cookies y autenticación
    allow_methods=["*"],     # Métodos HTTP permitidos (GET, POST, etc.)
    allow_headers=["*"],     # Headers permitidos
)
