# app/routers/restaurante.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Restaurante as RestauranteModel, User
from app.schemas import RestauranteCreate, Restaurante as RestauranteSchema
from app.oauth import get_current_user
from typing import Optional

router = APIRouter(
    prefix="/user/restaurante",
    tags=["Restaurante"],
)


@router.patch("/{id_restaurante}", response_model=RestauranteSchema, status_code=status.HTTP_200_OK)
def actualizar_o_crear_restaurante(
    id_restaurante: Optional[int] = None,
    restaurante: RestauranteCreate = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if id_restaurante:
        # Intentar actualizar un restaurante existente
        restaurante_existente = db.query(RestauranteModel).filter(
            RestauranteModel.id_restaurante == id_restaurante,
            RestauranteModel.owner_id == current_user.id_users
        ).first()
        if not restaurante_existente:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado o no autorizado")

        # Actualizar los campos proporcionados
        if restaurante.nombre_restaurante is not None:
            restaurante_existente.nombre_restaurante = restaurante.nombre_restaurante
        if restaurante.ciudad is not None:
            restaurante_existente.ciudad = restaurante.ciudad
        if restaurante.estado_provincia is not None:
            restaurante_existente.estado_provincia = restaurante.estado_provincia
        if restaurante.alcadia is not None:
            restaurante_existente.alcadia = restaurante.alcadia

        db.commit()
        db.refresh(restaurante_existente)
        return restaurante_existente
    else:
        # Crear un nuevo restaurante
        nuevo_restaurante = RestauranteModel(
            nombre_restaurante=restaurante.nombre_restaurante,
            ciudad=restaurante.ciudad,
            estado_provincia=restaurante.estado_provincia,
            alcadia=restaurante.alcadia,
            owner_id=current_user.id_users
        )
        db.add(nuevo_restaurante)
        db.commit()
        db.refresh(nuevo_restaurante)
        return nuevo_restaurante

@router.get("/", response_model=RestauranteSchema, status_code=status.HTTP_200_OK)
def obtener_restaurante(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Obtener el restaurante del usuario autenticado
    restaurante = db.query(RestauranteModel).filter(RestauranteModel.owner_id == current_user.id_users).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    return restaurante

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_restaurante(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Eliminar el restaurante del usuario autenticado
    restaurante = db.query(RestauranteModel).filter(RestauranteModel.owner_id == current_user.id_users).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    db.delete(restaurante)
    db.commit()
    return

@router.post("/", response_model=RestauranteSchema, status_code=status.HTTP_201_CREATED)
def crear_restaurante(
    restaurante: RestauranteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Crear un nuevo restaurante para el usuario autenticado
    nuevo_restaurante = RestauranteModel(
        nombre_restaurante=restaurante.nombre_restaurante,
        ciudad=restaurante.ciudad,
        estado_provincia=restaurante.estado_provincia,
        alcadia=restaurante.alcadia,
        owner_id=current_user.id_users
    )
    db.add(nuevo_restaurante)
    db.commit()
    db.refresh(nuevo_restaurante)
    return nuevo_restaurante