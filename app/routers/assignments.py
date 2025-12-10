# app/routers/assignments.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict

from app.db.database import get_db
from app.db.models import Tables as TablesModel, Waiter, User
from app.oauth import get_current_user 

router = APIRouter(
    prefix="/assignments",
    tags=["Assignments / Asignaciones"]
)

# 1. ASIGNAR MESERO A MESA
@router.post("/table/{table_number}/waiter/{waiter_uuid}", status_code=status.HTTP_200_OK)
def assign_waiter(
    table_number: int,
    waiter_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Buscar Mesa del Usuario
    table = db.query(TablesModel).filter(
        TablesModel.number == table_number,
        TablesModel.user_id == current_user.id_users
    ).first()
    
    if not table: raise HTTPException(404, "Mesa no encontrada")

    # Buscar Mesero del Usuario
    waiter = db.query(Waiter).filter(
        Waiter.uuid == waiter_uuid,
        Waiter.user_id == current_user.id_users
    ).first()
    
    if not waiter: raise HTTPException(404, "Mesero no encontrado")

    # Evitar duplicados
    if waiter in table.assigned_waiters:
        return {"message": "Este mesero ya estaba asignado a la mesa"}

    # Crear la relación
    table.assigned_waiters.append(waiter)
    db.commit()
    
    return {"message": f"Mesero {waiter.name} asignado a Mesa {table_number}"}

# 2. DESASIGNAR MESERO
@router.delete("/table/{table_number}/waiter/{waiter_uuid}", status_code=status.HTTP_200_OK)
def remove_assignment(
    table_number: int,
    waiter_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    table = db.query(TablesModel).filter(TablesModel.number == table_number, TablesModel.user_id == current_user.id_users).first()
    waiter = db.query(Waiter).filter(Waiter.uuid == waiter_uuid, Waiter.user_id == current_user.id_users).first()

    if not table or not waiter: raise HTTPException(404, "Mesa o Mesero no encontrado")

    if waiter not in table.assigned_waiters:
        raise HTTPException(400, "El mesero no está asignado a esta mesa")

    table.assigned_waiters.remove(waiter)
    db.commit()
    
    return {"message": "Asignación eliminada"}

# 3. VER ASIGNACIONES (Para tu Menu Cliente)
@router.get("/", response_model=List[Dict])
def get_all_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna una lista de todas las mesas activas y quién las atiende.
    Perfecto para pintar en el frontend.
    """
    tables = db.query(TablesModel).filter(
        TablesModel.user_id == current_user.id_users,
        TablesModel.is_active == True
    ).all()
    
    result = []
    for t in tables:
        waiters_info = [
            {"name": w.name, "uuid": w.uuid} 
            for w in t.assigned_waiters
        ]
        
        result.append({
            "table_number": t.number,
            "waiters": waiters_info
        })
        
    return result