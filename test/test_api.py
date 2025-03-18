from fastapi.testclient import TestClient
import sys 
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from main import app
from app.db.models import Base
from app.hashing import Hash
from app.db.database import get_db
import time 


db_path = os.path.join(os.path.dirname(__file__), 'test.db') #Ahi esta el sqllite
db_uri = "sqlite:///{}".format(db_path)
SQLALCHEMY_DATABASE_URL = db_uri
engine_test = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
Base.metadata.create_all(bind=engine_test)
cliente = TestClient(app)

def insertar_usuario_prueba():
# Usar una conexión explícita para ejecutar la consulta

   
    with engine_test.connect() as connection:
        password_hash = Hash.hash_password('123')
        connection.execute(
            text(f"""
                INSERT INTO users(name, email, password, rol) 
                VALUES ('Juan', 'moreno.@gmail.com', '{password_hash}', 'admin')
            """)
        )
        connection.commit()
insertar_usuario_prueba()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_crear_usuario():
    time.sleep(2)
    usuario = {
                "id_users": 8,
                "name": "Juan",
                "email": "juan123@gmail.com",
                "password": "123",
                "rol": "admin"
    }
    #response = cliente.post('/user/', json=usuario)
    #assert response.status_code == 201
    #assert response.json()["respuesta"] == 'Usuario creado correctamente'
    #pass

def test_delete_db():
    db_path = os.path.join(os.path.dirname(__file__), 'test.db') #Ahi esta el sqllite
    os.remove(db_path)