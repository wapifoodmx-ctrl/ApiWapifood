import os 
from dotenv import load_dotenv
from pathlib import Path


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


class Settings: 
    PROJECT_NAME: str = "PROYECTO_FASAPI_COMANDA"
    PROJECT_VERSION: str = "1.0"
    MYSQL_DB: str = os.getenv('MYSQL_DB')
    MYSQL_USER: str = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD: str = os.getenv('MYSQL_PASSWORD')
    MY_SQL_SERVER: str = os.getenv('MY_SQL_SERVER')
    MY_SQL_PORT: str = os.getenv('MY_SQL_PORT')
    DATABASE_URL = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MY_SQL_SERVER}:{MY_SQL_PORT}/{MYSQL_DB}'

settings = Settings()