from fastapi import APIRouter, Depends, status, Body, Request, HTTPException
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.schemas import Login, WaiterLoginSchema
from app.db.models import User, Waiter
from app.repository import auth
from app.token import create_access_token
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer


router = APIRouter(
    prefix="/login",
    tags=["Login"],
)
# Configura el esquema OAuth2
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/oauth2")
#@router.post("/", status_code=status.HTTP_200_OK)
@router.post("", status_code=status.HTTP_200_OK)
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



# --- NUEVO ENDPOINT PARA PRUEBAS (SIN PREFIJOS COMPLICADOS) ---
# app/routers/auth.py

@router.post("/test-token", status_code=status.HTTP_200_OK)
async def login_for_test(
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. Leer los datos del formulario
    form_data = await request.form()
    
    # DEBUG: Imprimir en consola qué rayos está llegando
    print(f"DEBUG DATOS RECIBIDOS: {form_data}")

    # 2. Buscar el email de forma segura (.get no da error si no existe)
    # Intentamos buscar 'username', si no está, buscamos 'email'
    email_val = form_data.get("username") or form_data.get("email")
    password_val = form_data.get("password")

    # 3. Validar que tengamos datos
    if not email_val or not password_val:
        raise HTTPException(
            status_code=400, 
            detail=f"Faltan credenciales. Se recibió: {list(form_data.keys())}"
        )

    # 4. Proceder con el login
    user = Login(email=email_val, password=password_val)
    auth_token = auth.auth_user(user, db)
    return auth_token


# 🆕 LOGIN ALTERNO PARA MESEROS
@router.post("/waiter", status_code=status.HTTP_200_OK)
async def login_waiter(
    credentials: WaiterLoginSchema,
    db: Session = Depends(get_db)
):
    """
    Login para Meseros.
    Requiere el email del Restaurante (Dueño) y el código de 6 dígitos del mesero.
    Genera un token con los permisos del Restaurante.
    """
    # 1. Buscar al Dueño del Restaurante por Email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        # Por seguridad, no decimos si el email existe o no, usamos mensaje genérico
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas (Restaurante no encontrado o código inválido)"
        )

    # 2. Buscar al Mesero que pertenezca a este usuario Y tenga el código correcto
    waiter = db.query(Waiter).filter(
        Waiter.user_id == user.id_users,      # 🔒 Candado: Debe ser de este restaurante
        Waiter.access_code == credentials.access_code # 🔒 Candado: Código exacto
    ).first()

    if not waiter:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Verifica el código de acceso."
        )

    # 3. Generar Token de Acceso
    # ⚠️ TRUCO CLAVE: Ponemos el email del DUEÑO en 'sub'.
    # Esto hace que 'get_current_user' en los otros endpoints crea que es el dueño,
    # otorgando acceso a productos, mesas y órdenes automáticamente.
    
    access_token = create_access_token(
        data={
            "sub": user.email,           # Identidad del Dueño (para permisos)
            "waiter_uuid": waiter.uuid,  # Guardamos quién es realmente (para logs futuros)
            "role": "waiter"             # Etiqueta opcional
        }
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "mesero_name": waiter.name, # Devolvemos el nombre para que el Front lo muestre
        "mesero_uuid": waiter.uuid,
        "restaurant_name": user.name
    }

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