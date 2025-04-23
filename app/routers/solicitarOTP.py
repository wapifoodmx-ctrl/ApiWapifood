from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import secrets
import pyotp
from app.schemas import User
from app.db.database import get_db
from app.utils.email import send_email
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    prefix="/otp",
    tags=["OTP"]
)

# Suponiendo que tienes un modelo User y una función get_db para la base de datos

@router.get("/generate-otp")
def generate_otp():
    # Generar un OTP de 6 dígitos
    otp = secrets.randbelow(10**6)
    otp_str = f"{otp:06}"  # Asegurarse de que tenga 6 dígitos con ceros iniciales
    return {"otp": otp_str}

@router.post("/register")
def register_user(username: str, password: str, db: Session = Depends(get_db)):
    otp_secret = pyotp.random_base32()
    new_user = User(username=username, password=password, otp_secret=otp_secret)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Usuario registrado", "otp_secret": otp_secret}

@router.post("/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Autenticar al usuario con correo y contraseña
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail="Credenciales inválidas")
    
    # Generar un OTP basado en el secreto del usuario
    totp = pyotp.TOTP(user.otp_secret)
    otp = totp.now()
    
    # Enviar el OTP al correo del usuario
    send_email(
        to_emails=[user.email],
        subject="Tu OTP de autenticación",
        body=f"Tu OTP es: {otp}"
    )
    
    return {"message": "Login exitoso, se ha enviado un OTP a tu correo"}

@router.post("/verify-otp")
def verify_otp(email: str, otp: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar el OTP
    totp = pyotp.TOTP(user.otp_secret)
    if not totp.verify(otp):
        raise HTTPException(status_code=400, detail="OTP inválido")
    
    user.is_otp_verified = True
    db.commit()
    return {"message": "OTP verificado exitosamente"}
