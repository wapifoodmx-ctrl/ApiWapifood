from fastapi import APIRouter, Depends, status
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.schemas import Login
from app.repository import auth
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    prefix="/login",
    tags=["Login"],
)


@router.post("/",status_code=status.HTTP_200_OK)  # Del diccionario que creamos se guardan los usuarios creados
def login(usuario:OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    auth_token = auth.auth_user(usuario, db)
    return auth_token