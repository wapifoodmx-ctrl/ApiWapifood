from fastapi import APIRouter, Depends, status, Body, Request, HTTPException
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.schemas import Login
from app.repository import auth
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer


router = APIRouter(
    prefix="/login",
    tags=["Login"],
)
# Configura el esquema OAuth2
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/oauth2")

@router.post("/", status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    content_type = request.headers.get("Content-Type")

    # Si es JSON
    if content_type == "application/json":
        try:
            user_data = await request.json()
            user = Login(**user_data)  # Valida y convierte el JSON al esquema Login
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    # Si es form-data (OAuth2)
    elif content_type == "application/x-www-form-urlencoded":
        form_data = await request.form()
        user = Login(email=form_data["username"], password=form_data["password"])
    
    # Si no es ninguno de los dos
    else:
        raise HTTPException(status_code=415, detail="Unsupported Media Type")

    auth_token = auth.auth_user(user, db)
    return auth_token

#@router.post("/oauth2", status_code=status.HTTP_200_OK)
#def login_oauth2(
     #form_data: OAuth2PasswordRequestForm = Depends(),  # Soporta form-data
     #db: Session = Depends(get_db)
# ):
     # Convierte form_data a Login
     #user = Login(email=form_data.username, password=form_data.password)
     #auth_token = auth.auth_user(user, db)
     #return auth_token


#@router.post("/json", status_code=status.HTTP_200_OK)
#def login_json(user: Login = Body(...), db: Session = Depends(get_db)):
 #   auth_token = auth.auth_user(user, db)
 #   return auth_token

# @router.post("/", status_code=status.HTTP_200_OK)
# def login(user: Login = Depends(), db: Session = Depends(get_db)):
#  auth_token = auth.auth_user(user, db)
#  return auth_token


#@router.post("/", status_code=status.HTTP_200_OK)
#def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    #user = Login(email=form_data.username, password=form_data.password)
    #auth_token = auth.auth_user(user, db)
    #return auth_token

#@router.post("/",status_code=status.HTTP_200_OK)  # Del diccionario que creamos se guardan los usuarios creados
#def login(user:OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#    auth_token = auth.auth_user(user, db)
#    return auth_token