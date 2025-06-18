from enum import Enum



#Para el rol de los usuarios
#La enumeración es una lista de valores que se pueden asignar a una variable.
#En este caso, el rol puede ser "admin
#user" o "client".
#El modelo de datos se puede usar para validar y serializar datos.
#La enumeración es una lista de valores que se pueden asignar a una variable.
class RoleEnum(str, Enum):
    admin ="admin"
    user ="user"
    client ="client"

#Para el rol de las mesas 
#En este caso, el rol puede ser "admin
class RoleOrders(str, Enum):
    Libre ="Libre"
    Ocupado ="Ocupado"


#Clases de enum para las mesas identificar ocupado y libre 
class TablesEnum(str, Enum):
    Libre ="Libre"
    Ocupado ="Ocupado"

class SubscriptionAmount(Enum):
    PLAN_100 = 100  # 1 mesa
    PLAN_200 = 200  # 16 mesas
    PLAN_300 = 300  # 26 mesas

#Para el metodo de pago
#La enumeración es una lista de valores que se pueden asignar a una variable.
class PaymentMethodEnum(str, Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    pasarela = "pasarela"


# Definir los tipos de planes disponibles como un Enum
class PlanType(str, Enum):
    BASICO = "basico"
    PROFESIONAL = "profesional"
    EMPRESARIAL = "empresarial"



class StatusEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"




class OrderStatusEnum(str, Enum):
    Pendiente = "Pendiente"
    EnCocina = "EnCocina"
    Preparado = "Preparado"
    Cancelado = "Cancelado"
    Completado = "Completado"
    Finalizado = "Finalizado"


class PagosEnOrders(str, Enum):
    Efectivo = "Efectivo"
    Tarjeta = "Tarjeta"

    