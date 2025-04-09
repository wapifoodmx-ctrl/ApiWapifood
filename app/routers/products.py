from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Annotated, Optional
from app.db.database import get_db
from app.db.models import Image, User
from app.schemas import ImageCreate, ImageResponse
from app.db.models import Products as ProductsModel, Orders as OrdersModel, OrdersDetails as OrdersDetailsModel, User, Image as ImageModel
from app.schemas import Products as ProductsSchema, ProductsCreate, ProductsPatch, Orders as OrdersSchema, OrdersDetails as OrdersDetailsSchema
from app.oauth import get_current_user
from datetime import datetime
from pathlib import Path
from app.db.models import Categoria
from app.db.models import StatusEnum, RoleOrders
import json
# from pydantic import ValidationError
import uuid


router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )
# Directorio donde se guardarán las imágenes
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Esquema OAuth2 para el token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@router.get("/", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def obtenemos_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los productos creados por el usuario autenticado, incluyendo la URL de la imagen."""
    # Obtener los productos del usuario autenticado
    productos = db.query(ProductsModel).filter(ProductsModel.owner_id == current_user.id_users).all()

    # Lista para almacenar los productos con la URL de la imagen
    productos_con_imagen = []

    for producto in productos:
        # Obtener la primera imagen asociada al producto (si existe)
        imagen = producto.images[0] if producto.images else None
        # Generar la URL de la imagen (si existe)
        image_url = f"http://192.168.1.69:8000/static/uploads/{imagen.file_name}" if imagen else None
        # Convertir el producto a ProductsSchema y agregar la URL de la imagen
        producto_schema = ProductsSchema.from_orm(producto)
        producto_schema.image_url = image_url
        productos_con_imagen.append(producto_schema)

    return productos_con_imagen

@router.get("/{product_id}", response_model=ProductsSchema, status_code=status.HTTP_200_OK)
def obtener_producto_id(
    product_id: Annotated[int, "ID del producto a buscar"],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ProductsSchema:
    """
    Obtiene un producto específico por su ID, si pertenece al usuario autenticado.

    Args:
        product_id: ID del producto a buscar.
        db: Sesión de la base de datos.
        current_user: Usuario autenticado.

    Raises:
        HTTPException: 404 si el producto no existe.
        HTTPException: 403 si el producto no pertenece al usuario.

    Returns:
        ProductsSchema: Esquema del producto encontrado.
    """
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
            detail="No tienes permiso para acceder a este producto"
        )
    
    # Convertimos el modelo SQLAlchemy al esquema Pydantic
    return ProductsSchema.from_orm(db_product)


@router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
async def crear_producto_con_imagen(
    product: str,  # Cambiamos a str para aceptar la cadena JSON desde Swagger UI
    file: UploadFile = File(None),  # Imagen opcional
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea un nuevo producto con una imagen opcional, asignando el owner_id del usuario autenticado,
    y genera un pedido y detalle de pedido."""
    
    # 1. Parsear la cadena JSON a un objeto ProductsCreate
    try:
        product_dict = json.loads(product)  # Convertimos la cadena JSON a un diccionario
        product_data = ProductsCreate(**product_dict)  # Validamos contra el esquema ProductsCreate
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="El formato JSON del campo 'product' es inválido")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos del producto inválidos: {str(e)}")

    # 2. Validar la cantidad
    if product_data.quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que 0")

    # 3. Validar que la categoría exista
    if product_data.category_id:
        category_exists = db.query(Categoria).filter(Categoria.id_categoria == product_data.category_id).first()
        if not category_exists:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
    else:
        raise HTTPException(status_code=400, detail="Se requiere una categoría (category_id)")

    # 4. Crear el producto en la base de datos
    db_product = ProductsModel(
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        status=product_data.status or StatusEnum.activo,  # Usamos el valor por defecto de StatusEnum
        category_id=product_data.category_id,
        owner_id=current_user.id_users
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # 5. Manejar la subida de imagen si se proporciona
    if file:
        # Validar el tipo de archivo
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        
        # Validar la extensión
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}
        file_extension = f".{file.filename.split('.')[-1].lower()}"
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Solo se permiten imágenes con extensiones .jpg, .jpeg, .png o .gif")
        
        # Generar nombre único y guardar la imagen
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Crear registro de la imagen en la base de datos
        db_image = ImageModel(
            file_name=unique_filename,
            file_path=str(file_path),
            user_id=current_user.id_users,
            product_id=db_product.id_products
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

    # 6. Crear un pedido asociado al usuario autenticado
    quantity = product_data.quantity
    db_order = OrdersModel(
        state=RoleOrders.Ocupado,  # Usamos el enum RoleOrders
        date_time=datetime.utcnow(),
        total=db_product.price * quantity,
        orderscol="Orden creada automáticamente",
        user_id=current_user.id_users,
        product_name=db_product.name
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 7. Crear detalle de pedido
    unit_price = db_product.price
    subtotal = quantity * unit_price
    db_order_detail = OrdersDetailsModel(
        order_id=db_order.id_orders,
        product_id=db_product.id_products,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal
    )
    db.add(db_order_detail)
    db.commit()
    db.refresh(db_order_detail)

    # 8. Devolver el producto creado
    return ProductsSchema.from_orm(db_product)


# Actualiza un producto existente
# Se espera un JSON con los campos a actualizar y una imagen opcional
# Se valida que el producto pertenezca al usuario autenticado
# Se actualiza la imagen si se proporciona una nueva
@router.patch("/{product_id}", response_model=ProductsSchema, status_code=status.HTTP_200_OK)
async def actualizar_producto(
    product_id: int,
    product_update: str,
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    try:
        product_dict = json.loads(product_update)
        product_data = ProductsPatch(**product_dict)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="El formato JSON del campo 'product_update' es inválido")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos del producto inválidos: {str(e)}")

    db_product = db.query(ProductsModel).filter(ProductsModel.id_products == product_id).first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto con ID {product_id} no encontrado")
    
    if db_product.owner_id != current_user.id_users:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para modificar este producto")

    if product_data.category_id:
        category_exists = db.query(Categoria).filter(Categoria.id_categoria == product_data.category_id).first()
        if not category_exists:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

    if file:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}
        file_extension = f".{file.filename.split('.')[-1].lower()}"
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Solo se permiten imágenes con extensiones .jpg, .jpeg, .png o .gif")
        
        db_image = db.query(ImageModel).filter(ImageModel.product_id == product_id).first()
        if db_image:
            old_image_path = Path(db_image.file_path)
            if old_image_path.exists():
                try:
                    old_image_path.unlink()
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error al eliminar la imagen anterior: {str(e)}")
            db.delete(db_image)
            db.commit()

        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        db_image = ImageModel(
            file_name=unique_filename,
            file_path=str(file_path),
            user_id=current_user.id_users,
            product_id=db_product.id_products
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

    if product_data.name is not None:
        db_product.name = product_data.name
    if product_data.description is not None:
        db_product.description = product_data.description
    if product_data.price is not None:
        db_product.price = product_data.price
    if product_data.status is not None:
        db_product.status = product_data.status
    if product_data.category_id is not None:
        db_product.category_id = product_data.category_id
    
    db.commit()
    db.refresh(db_product)

    db_image = db.query(ImageModel).filter(ImageModel.product_id == product_id).first()
    image_url = f"http://localhost:8000/static/uploads/{db_image.file_name}" if db_image else None

    response = ProductsSchema(
        id_products=db_product.id_products,
        name=db_product.name,
        description=db_product.description,
        price=float(db_product.price),
        status=db_product.status,
        category_id=db_product.category_id,  # Ahora usamos category_id
        owner_id=db_product.owner_id,
        image_url=image_url
    )
    return response


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Elimina un producto si pertenece al usuario autenticado y elimina la imagen asociada si existe."""
    # 1. Buscamos el producto por ID
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
    
    # 2. Buscar la imagen asociada al producto
    db_image = db.query(ImageModel).filter(ImageModel.product_id == product_id).first()
    if db_image:
        # Eliminar la imagen del sistema de archivos
        image_path = Path(db_image.file_path)
        if image_path.exists():
            try:
                image_path.unlink()  # Eliminar el archivo
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al eliminar la imagen del sistema de archivos: {str(e)}"
                )
        
        # Eliminar el registro de la imagen de la base de datos
        db.delete(db_image)
        db.commit()

    # 3. Eliminamos el producto
    db.delete(db_product)
    db.commit()
    
    return None  # HTTP 204 No Content no devuelve cuerpo