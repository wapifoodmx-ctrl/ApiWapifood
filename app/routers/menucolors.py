from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
# Importamos el Modelo Nuevo y la tabla de Usuarios
from app.db.models import Menucolors, User 
# Importamos los Schemas
from app.schemas import MenucolorsCreate, MenucolorsUpdate, MenucolorsResponse
# ⚠️ IMPORTANTE: Ajusta este import según donde tengas tu función 'get_current_user'
# (Generalmente está en oauth2.py o auth.py)
from app.repository.auth import get_current_user
router = APIRouter(
    prefix="/menucolors",
    tags=["Menu Colors / Config"]
)

# 1. GET ALL (Traer todas mis configuraciones)
@router.get("/", response_model=List[MenucolorsResponse])
def get_my_menucolors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 Filtramos por el ID del usuario logueado
    return db.query(Menucolors).filter(Menucolors.user_id == current_user.id_users).all()


# 2. GET BY KEY (Traer una configuración específica, ej: "font_size")
@router.get("/{key}", response_model=MenucolorsResponse)
def get_menucolor_by_key(
    key: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 Buscamos coincidencia de Clave Y Usuario
    item = db.query(Menucolors).filter(
        Menucolors.key == key,
        Menucolors.user_id == current_user.id_users
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Configuración '{key}' no encontrada")
    return item


# 3. POST (Crear nueva configuración)
@router.post("/", response_model=MenucolorsResponse, status_code=status.HTTP_201_CREATED)
def create_menucolor(
    config: MenucolorsCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar si ya existe esa clave PARA ESTE USUARIO
    existing = db.query(Menucolors).filter(
        Menucolors.key == config.key,
        Menucolors.user_id == current_user.id_users
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"La clave '{config.key}' ya existe. Usa PATCH para editarla."
        )
    
    # 2. Crear asignando el usuario
    new_item = Menucolors(
        key=config.key,
        value=config.value,
        description=config.description,
        group=config.group,
        user_id=current_user.id_users # 🔒 Asignamos dueño
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


# 4. PATCH (Actualizar valor)
@router.patch("/{key}", response_model=MenucolorsResponse)
def update_menucolor(
    key: str, 
    config_update: MenucolorsUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 Buscar solo si me pertenece
    item = db.query(Menucolors).filter(
        Menucolors.key == key,
        Menucolors.user_id == current_user.id_users
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Configuración '{key}' no encontrada")
    
    # Actualizar campos si vienen en el body
    if config_update.value is not None:
        item.value = config_update.value
    if config_update.description is not None:
        item.description = config_update.description
    if config_update.group is not None:
        item.group = config_update.group
        
    db.commit()
    db.refresh(item)
    return item


# 5. DELETE (Borrar configuración)
@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menucolor(
    key: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 Buscar solo si me pertenece
    item = db.query(Menucolors).filter(
        Menucolors.key == key,
        Menucolors.user_id == current_user.id_users
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Configuración '{key}' no encontrada")
    
    db.delete(item)
    db.commit()
    return None