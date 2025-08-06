from fastapi import FastAPI, Depends, HTTPException, status
import uvicorn
from app.routers import user, tables, products, orders, payments, auth, categoria, solicitarOTP, analytics #restaurante
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
from typing import List, Dict
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import FormData
from fastapi.security import HTTPBasic, HTTPBasicCredentials

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")
# Lista de clientes WebSocket con user_id
websocket_clients: List[Dict[str, WebSocket | int]] = []
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
security = HTTPBasic()
app.include_router(user.router)
#app.include_router(solicitarOTP.router)
#app.include_router(restaurante.router)
app.include_router(auth.router)
# Incluir los routers con prefijos específicos
app.include_router(categoria.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(analytics.router)
app.include_router(tables.router)
app.include_router(payments.router)


#--------------------------------------
# SECURIDAD EN LA DOCUMEN TACION  # 





#--------------------------------------
#--------------------------------------


# Montar el directorio de archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Montar explícitamente el subdirectorio uploadsUser
#app.mount("/staticUser/uploadsUser", StaticFiles(directory="staticUser/uploadsUser"), name="uploadsUser")

# Configuración de CORS
origins = [
    "http://localhost:3000",  # Origen de tu frontend
    "http://localhost:5173",  # Otro puerto común para Vite/React
    "http://127.0.0.1:3000",  # Variación del localhost
    # Agrega más orígenes según necesites
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lista de orígenes permitidos
    allow_credentials=True,  # Permitir cookies y autenticación
    allow_methods=["*"],     # Métodos HTTP permitidos (GET, POST, etc.)
    allow_headers=["*"],     # Headers permitidos
)

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     return JSONResponse(
#         status_code=422,
#         content={"detail": exc.errors(), "body": exc.body},
#     )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # Convertir FormData a un diccionario si es necesario
    body = None
    if isinstance(exc.body, FormData):
        body = {key: value for key, value in exc.body.items()}
    else:
        body = exc.body

    return JSONResponse(
        status_code=422,
        content={
            "detail": errors,
            "body": body
        },
    )

if __name__ == "__main__":
    uvicorn.run("main:app",host="0.0.0.0", port = 8000, reload=True)
