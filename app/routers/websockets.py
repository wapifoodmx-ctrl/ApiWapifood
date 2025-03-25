# app/routers/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.db.models import User
from jose import JWTError, jwt
from app.token import SECRET_KEY, ALGORITHM
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Dict[str, WebSocket | int]] = []

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append({"websocket": websocket, "user_id": user_id})

    def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections.remove({"websocket": websocket, "user_id": user_id})

    async def send_personal_message(self, message: str, user_id: int):
        for connection in self.active_connections:
            if connection["user_id"] == user_id:
                await connection["websocket"].send_text(message)

manager = ConnectionManager()

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
    await manager.send_personal_message(message, user_id)

# Endpoint WebSocket autenticado con token como query parameter
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """Maneja conexiones WebSocket autenticadas con token JWT pasado como query parameter."""
    try:
        # Verificar el token y obtener el usuario
        user = await get_user_from_token(token, db)
        user_id = user.id_users

        # Aceptar la conexión
        await manager.connect(websocket, user_id)

        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"Echo: {data}")
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
            await notify_clients("user_disconnected", {"user_id": user_id}, user_id)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))