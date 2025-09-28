# from fastapi import FastAPI, Depends, HTTPException, status
# import uvicorn
# from app.routers import user, tables, products, orders, payments, auth, categoria, solicitarOTP, analytics #restaurante
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi import WebSocket
# from typing import List, Dict
# from fastapi.security import OAuth2PasswordBearer
# from fastapi.responses import JSONResponse
# from fastapi.exceptions import RequestValidationError
# from fastapi import Request
# from fastapi.staticfiles import StaticFiles
# from starlette.datastructures import FormData
# from fastapi.security import HTTPBasic, HTTPBasicCredentials

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")
# # Lista de clientes WebSocket con user_id
# websocket_clients: List[Dict[str, WebSocket | int]] = []
# #def creeate_tables():
# # Base.metadata.create_all(bind=engine)
# #creeate_tables()
# #Definimos la enumeracion para el rol de la comanda
# #Y la insertamos en la clase siguiente para reconocer el rol
# #get para solicitar datos 
# #post para enviar datos
# #put para actualizar datos
# #delete para eliminar datos
# app = FastAPI() 
# security = HTTPBasic()
# app.include_router(user.router)
# #app.include_router(solicitarOTP.router)
# #app.include_router(restaurante.router)
# app.include_router(auth.router)
# # Incluir los routers con prefijos específicos
# app.include_router(categoria.router)
# app.include_router(products.router)
# app.include_router(orders.router)
# app.include_router(analytics.router)
# app.include_router(tables.router)
# app.include_router(payments.router)


# #--------------------------------------
# # SECURIDAD EN LA DOCUMEN TACION  # 





# #--------------------------------------
# #--------------------------------------


# # Montar el directorio de archivos estáticos
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# # Montar explícitamente el subdirectorio uploadsUser
# #app.mount("/staticUser/uploadsUser", StaticFiles(directory="staticUser/uploadsUser"), name="uploadsUser")

# # Configuración de CORS
# origins = [
#     "http://localhost:3000",  # Origen de tu frontend
#     "http://localhost:5173",  # Otro puerto común para Vite/React
#     "http://127.0.0.1:3000",  # Variación del localhost
#     # Agrega más orígenes según necesites
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Lista de orígenes permitidos
#     allow_credentials=True,  # Permitir cookies y autenticación
#     allow_methods=["*"],     # Métodos HTTP permitidos (GET, POST, etc.)
#     allow_headers=["*"],     # Headers permitidos
# )

# # @app.exception_handler(RequestValidationError)
# # async def validation_exception_handler(request: Request, exc: RequestValidationError):
# #     return JSONResponse(
# #         status_code=422,
# #         content={"detail": exc.errors(), "body": exc.body},
# #     )


# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     errors = exc.errors()
#     # Convertir FormData a un diccionario si es necesario
#     body = None
#     if isinstance(exc.body, FormData):
#         body = {key: value for key, value in exc.body.items()}
#     else:
#         body = exc.body

#     return JSONResponse(
#         status_code=422,
#         content={
#             "detail": errors,
#             "body": body
#         },
#     )

# if __name__ == "__main__":
#     uvicorn.run("main:app",host="0.0.0.0", port = 8000, reload=True)




from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.datastructures import FormData
from typing import List, Dict
import uvicorn

# Rutas
from app.routers import user, tables, products, orders, payments, auth, categoria, solicitarOTP, analytics, free

# Seguridad
security = HTTPBasic()
oauth2_scheme = None  # No usado directamente aquí

# Desactivar documentación pública
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    title="Mi API Protegida"
)

# WebSocket
websocket_clients: List[Dict[str, WebSocket | int]] = []

# Incluir routers
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(categoria.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(analytics.router)
app.include_router(tables.router)
app.include_router(payments.router)
app.include_router(free.router)


# Archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manejo de errores de validación
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
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

# RUTA PROTEGIDA PARA LA DOCUMENTACIÓN SWAGGER
@app.get("/api_wapi", include_in_schema=False)
def get_docs(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "wapi" or credentials.password != " ":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Documentación Privada")

# RUTA PROTEGIDA PARA EL ESQUEMA OPENAPI
@app.get("/openapi.json", include_in_schema=False)
def openapi(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "wapi" or credentials.password != "W4p1T3cH-W4p1F00d":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )
    return get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )

# Ejecutar la app  y abre: http://localhost:8000/secret-docs
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
