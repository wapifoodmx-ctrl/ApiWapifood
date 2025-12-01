from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
# Importamos el Modelo Nuevo y la tabla de Usuarios
from app.db.models import Menucolors, User 
# Importamos los Schemas
from app.schemas import MenucolorRequest, MenucolorResponse
# ⚠️ IMPORTANTE: Ajusta este import según donde tengas tu función 'get_current_user'
# (Generalmente está en oauth2.py o auth.py)
from app.repository.auth import get_current_user
router = APIRouter(
    prefix="/menucolors",
    tags=["Menu Colors / Config"]

    
)
# 1. GET: Obtener mi color actual
@router.get("/", response_model=MenucolorResponse)
def get_my_color(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Buscamos directamente por el ID del usuario
    item = db.query(Menucolors).filter(Menucolors.user_id == current_user.id_users).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="No has configurado un color aún")
    return item

# 2. POST/PUT: Guardar o Actualizar mi color (Todo en uno)
@router.post("/", response_model=MenucolorResponse)
def save_my_color(
    data: MenucolorRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Buscamos si ya existe
    item = db.query(Menucolors).filter(Menucolors.user_id == current_user.id_users).first()
    
    if item:
        # Si existe, actualizamos
        item.color = data.color
    else:
        # Si no existe, creamos
        item = Menucolors(
            user_id=current_user.id_users,
            color=data.color
        )
        db.add(item)
    
    db.commit()
    db.refresh(item)
    return item

# 3. DELETE: Borrar mi color (volver al default)
@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_color(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(Menucolors).filter(Menucolors.user_id == current_user.id_users).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="No hay configuración para borrar")
    
    db.delete(item)
    db.commit()
    return None


# 4. PATCH: Actualizar mi color (Solo si ya existe)
@router.patch("/", response_model=MenucolorResponse)
def update_my_color(
    data: MenucolorRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Buscamos el registro del usuario
    item = db.query(Menucolors).filter(Menucolors.user_id == current_user.id_users).first()
    
    # 2. Si no existe, no podemos "parchear" nada -> Error 404
    if not item:
        raise HTTPException(
            status_code=404, 
            detail="No tienes un color configurado para actualizar. Crea uno primero con POST."
        )
    
    # 3. Actualizamos el valor
    item.color = data.color
    db.commit()
    db.refresh(item)
    
    return item