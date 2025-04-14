# app/routers/restaurante.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas import RestauranteCreate
from app.repository.user import create_restaurante
from app.oauth import get_current_user
from app.db.models import User

router = APIRouter(
    prefix="/restaurantes",
    tags=["Restaurantes"],
)



@router.post("/", response_model=RestauranteCreate)
def create_restaurante_router(
    restaurante: RestauranteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Obtener el usuario autenticado
):
    db_restaurante = create_restaurante(
        db=db,
        nombre_restaurante=restaurante.nombre_restaurante,
        ciudad=restaurante.ciudad,
        estado_provincia=restaurante.estado_provincia,
        alcadia=restaurante.alcadia,
        owner_id=current_user.id_users  # Usar el ID del usuario autenticado
    )
    return db_restaurante