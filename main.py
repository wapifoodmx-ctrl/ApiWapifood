from fastapi import FastAPI, HTTPException, Depends
import uvicorn
from app.routers import user, tables, products, orders, payments, auth
from app.db.database import Base, engine, get_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
from app.schemas import Products as ProductsSchema
from app.oauth import get_current_user
from app.db.models import Products as ProductsModel
from sqlalchemy.orm import Session
from app.db.models import User
import json
from  app.token import SECRET_KEY, ALGORITHM 
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer



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
app.include_router(user.router)
app.include_router(auth.router)
# Incluir los routers con prefijos específicos
app.include_router(tables.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)



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

# Función para verificar el token y obtener el user_id
async def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = db.query(User).filter(User.email == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

# Función para notificar a clientes WebSocket
async def notify_clients(event_type: str, data: dict, user_id: int):
    """Notifica a los clientes WebSocket conectados según el user_id."""
    message = json.dumps({"event_type": event_type, "data": data})
    for client in websocket_clients:
        if client["user_id"] == user_id:
            await client["websocket"].send_text(message)

# Endpoint WebSocket autenticado con token
# Endpoint WebSocket autenticado con token como query parameter
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """Maneja conexiones WebSocket autenticadas con token JWT pasado como query parameter."""
    try:
        # Verificar el token y obtener el usuario
        user = await get_user_from_token(token, db)
        user_id = user.id_users

        # Aceptar la conexión
        await websocket.accept()
        websocket_clients.append({"websocket": websocket, "user_id": user_id})

        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"Echo: {data}")
        except WebSocketDisconnect:
            websocket_clients.remove({"websocket": websocket, "user_id": user_id})
            await notify_clients("user_disconnected", {"user_id": user_id}, user_id)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)  # Cerrar con mensaje de error
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))

# Ruta para crear productos (sin validación de duplicados)
@app.post("/products/", response_model=ProductsSchema)
async def create_product(
    product: ProductsSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_product = ProductsModel(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        category=product.category,
        owner_id=current_user.id_users
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    # Notificar creación de producto
    product_data = ProductsSchema.from_orm(db_product).dict()
    await notify_clients("product_created", product_data, current_user.id_users)
    return ProductsSchema.from_orm(db_product)


if __name__ == "__main__":
    uvicorn.run("main:app", port = 8000, reload=True)
