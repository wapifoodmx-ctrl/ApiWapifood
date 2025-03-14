from fastapi import APIRouter
from app.schemas import User, UserId
from typing import List
from app.schemas import Tables
from fastapi import HTTPException
from app.schemas import Tables

tables: List[Tables] = []


 
router = APIRouter()


@router.post("/tables", response_model=dict) #Creamos las mesas
def crear_mesa(table: Tables):
    tables.append(table)
    return {"mensaje": "Mesa creada exitosamente"}



@router.get("/tables", response_model=List[Tables]) #Obtenemos las mesas
def obtener_las_mesas():
    return tables



@router.put("/tables/{table_id}")#Actualizamos las mesas
def actualizamos_mesa(table_id: int, table: Tables):#Actualizamos las mesas apartir del id de la mesa y la mesa 
    for index, t in enumerate(tables):
        if t.id_tables == table_id:
            tables[index] = table
            return {"mensaje": "Mesa actualizada"}
    raise HTTPException(status_code=404, detail="Mesa no encontrada")
