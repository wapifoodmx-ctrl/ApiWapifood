from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Products as ProductsModel, Orders as OrdersModel, OrdersDetails as OrdersDetailsModel, User
from app.schemas import Products as ProductsSchema, ProductsCreate, Orders as OrdersSchema, OrdersDetails as OrdersDetailsSchema
from app.oauth import get_current_user
from datetime import datetime

 
router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )

# Esquema OAuth2 para el token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.get("/", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def obtenemos_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los productos creados por el usuario autenticado."""
    productos = db.query(ProductsModel).filter(ProductsModel.owner_id == current_user.id_users).all()
    return [ProductsSchema.from_orm(producto) for producto in productos]



@router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
def crear_producto_owner(
    product: ProductsCreate,  # Usar el esquema ProductsCreate
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea un nuevo producto asignando el owner_id del usuario autenticado, y genera un pedido y detalle de pedido."""
    # 1. Validar la cantidad
    if product.quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que 0")

    # 2. Crear el producto
    db_product = ProductsModel(
        name=product.name,
        description=product.description,
        price=product.price,
        status=product.status or "activo",  # Usar el valor por defecto de StatusEnum
        category=product.category,
        owner_id=current_user.id_users
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # 3. Crear un pedido (Orders) asociado al usuario autenticado
    quantity = product.quantity  # Cantidad proporcionada en la solicitud
    db_order = OrdersModel(
        mesa_id=product.mesa_id,  # Usar el mesa_id proporcionado
        state="Ocupado",  # Estado inicial del pedido (RoleOrders.Ocupado)
        date_time=datetime.utcnow(),
        total=db_product.price * quantity,  # Total inicial basado en el precio del producto y la cantidad
        orderscol="Orden creada automáticamente",
        user_id=current_user.id_users, # Asociar el pedido al usuario autenticado
        product_name=db_product.name    # Tomar el nombre del producto
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 4. Crear un detalle de pedido (OrdersDetails) tomando datos de Products y Orders
    unit_price = db_product.price  # Tomar el precio del producto
    subtotal = quantity * unit_price  # Calcular el subtotal

    db_order_detail = OrdersDetailsModel(
        order_id=db_order.id_orders,  # Tomar el ID del pedido recién creado
        product_id=db_product.id_products,  # Tomar el ID del producto recién creado
        quantity=quantity,  # Usar la cantidad proporcionada
        unit_price=unit_price,  # Usar el precio del producto
        subtotal=subtotal  # Calcular el subtotal
    )
    db.add(db_order_detail)
    db.commit()
    db.refresh(db_order_detail)

    return ProductsSchema.from_orm(db_product)





""" @router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
def crear_producto_owner(
    product: ProductsSchema,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    db_product = ProductsModel(
        name=product.name,
        description=product.description,
        price=product.price,
        status=product.status,
        category=product.category,
        owner_id=current_user.id_users
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return ProductsSchema.from_orm(db_product) """

@router.put("/{product_id}", response_model=ProductsSchema, status_code=status.HTTP_200_OK)
def actualizar_producto(
    product_id: int,
    product_update: ProductsSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Actualiza un producto existente si pertenece al usuario autenticado."""
    # Buscamos el producto por ID
    db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
    
    # Verificamos si el producto existe
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    # Verificamos si el producto pertenece al usuario autenticado
    if db_product.owner_id != current_user.id_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este producto"
        )
    
    # Actualizamos los campos del producto
    db_product.name = product_update.name
    db_product.description = product_update.description
    db_product.price = product_update.price
    db_product.status = product_update.status
    db_product.category = product_update.category
    
    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(db_product)
    
    return ProductsSchema.from_orm(db_product)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Elimina un producto si pertenece al usuario autenticado."""
    # Buscamos el producto por ID
    db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
    
    # Verificamos si el producto existe
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    # Verificamos si el producto pertenece al usuario autenticado
    if db_product.owner_id != current_user.id_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este producto"
        )
    
    # Eliminamos el producto
    db.delete(db_product)
    db.commit()
    
    return None  # HTTP 204 No Content no devuelve cuerpo