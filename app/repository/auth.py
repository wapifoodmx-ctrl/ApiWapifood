from sqlalchemy.orm import Session
from app.db import models
from fastapi import HTTPException, status
from app.hashing import Hash
from app.token import create_access_token
from datetime import timedelta

def auth_user(usuario, db:Session):
    user = db.query(models.User).filter(models.User.email == usuario.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"""Usuario no encontrado con el {usuario.email}"""
        )
    #print("Este es la contraseña : ---->", Hash.verify_password(usuario.password, user.password))
    if not Hash.verify_password(usuario.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta"
        )

    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}