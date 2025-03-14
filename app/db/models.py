from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum, DateTime, Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from app.db.database import Base

"""

class User(BaseModel):
    id_users: int
    name: str
    email: str
    password: str
    rol: RoleEnum  

class UserId(BaseModel):
    id_user:int


class RoleEnum(str, Enum):
    admin ="admin"
    user ="user"
    client ="client"



"""

class  RoleEnum(str, SQLAlchemyEnum):
    _tablename__ = "RolesUrsers"
    admin = "admin"
    user = "user"
    client = "client"

class RoleOrders(str, SQLAlchemyEnum):
    _tablename__ = "RolesOrders"
    Libre = "Libre"
    Ocupado = "Ocupado"

class TablesEnum(str, SQLAlchemyEnum):
    _tablename__ = "Tables"
    Libre = "Libre"
    Ocupado = "Ocupado"

class CategoryEnum(str, SQLAlchemyEnum):
    _tablename__ = "Categories"
    input = "input"
    output = "output"

class PaymentMethodEnum(str, SQLAlchemyEnum):   
    _tablename__ = "PaymentMethods"
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"


class User(Base):
    __tablename__ = "users"
    id_users = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50))
    email = Column(String(50))
    password = Column(String(50))
    rol = Column(String(50))


class Orders(Base):
    __tablename__ = "orders"
    id_orders = Column(Integer, primary_key=True, autoincrement=True)
    mesa_id = Column(Integer)
    state = Column(String(50))
    date_time = Column(DateTime)
    total = Column(Decimal)
    orderscol = Column(String(50))
