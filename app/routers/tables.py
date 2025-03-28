from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Tables as TablesModel  # Modelo de SQLAlchemy
from app.schemas import Tables as TablesSchema  # Esquema Pydantic
from app.repository.auth import get_current_user
from app.db.models import User
from fastapi.security import OAuth2PasswordBearer


router = APIRouter(
    prefix="/tables",
    tags=["Tables"]
)
# Esquema para obtener el token del encabezado Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.post("/tables", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_mesa(
    table: TablesSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Ya está correcto
):
    """Crea una nueva mesa en la base de datos, asignando el user_id del usuario autenticado."""
    # Verificar si la mesa ya existe (por número, por ejemplo)
    existing_table = db.query(TablesModel).filter(TablesModel.number == table.number).first()
    if existing_table:
        raise HTTPException(status_code=400, detail="El número de mesa ya existe")
    
    # Crear nueva mesa
    try:
        db_table = TablesModel(
            number=table.number,
            capacity=table.capacity,
            state=table.state,
            user_id=current_user.id_users  # Asignar el user_id del usuario autenticado
        )
        db.add(db_table)
        db.commit()
        db.refresh(db_table)
        return {"mensaje": "Mesa creada exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando mesa: {str(e)}")

@router.get("/tables", response_model=List[TablesSchema], status_code=status.HTTP_200_OK)
def obtener_las_mesas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Corregir aquí
):
    """Obtiene todas las mesas de la base de datos."""
    # Filtrar las mesas por el usuario autenticado (opcional)
    mesas = db.query(TablesModel).filter(TablesModel.user_id == current_user.id_users).all()
    return mesas

@router.put("/tables/{table_id}", response_model=dict, status_code=status.HTTP_200_OK)
def actualizamos_mesa(
    table_id: int,
    table: TablesSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Corregir aquí
):
    """Actualiza una mesa existente en la base de datos."""
    db_table = db.query(TablesModel).filter(TablesModel.id_tables == table_id).first()
    if db_table is None:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    # Verificar si el usuario tiene permiso para actualizar la mesa
    if db_table.user_id != current_user.id_users:
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar esta mesa")

    # Actualizar los campos
    try:
        for key, value in table.dict().items():
            setattr(db_table, key, value)
        db.commit()
        db.refresh(db_table)
        return {"mensaje": "Mesa actualizada exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando mesa: {str(e)}")