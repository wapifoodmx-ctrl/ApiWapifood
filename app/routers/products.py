from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Annotated, Optional
from app.db.database import get_db
from app.db.models import Image, User
from app.schemas import ImageCreate, ImageResponse, TopProduct
from app.db.models import Products as ProductsModel, Orders as OrdersModel, OrdersDetails as OrdersDetailsModel, User, Image as ImageModel
from app.schemas import Products as ProductsSchema, ProductsCreate, Orders as OrdersSchema, OrdersDetails as OrdersDetailsSchema
from app.oauth import get_current_user
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
from app.repository import products as product_repo
from app.repository.products import get_top_products


router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )
# Directorio donde se guardarán las imágenes
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Esquema OAuth2 para el token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


# Mover esta ruta ANTES de las rutas dinámicas con {product_id}
@router.get("/top", status_code=status.HTTP_200_OK, response_model=List[TopProduct], description="Obtiene los productos más populares con su nombre, precio, unidades vendidas y subtotal.")
def get_top_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Obtener el user_id del usuario autenticado
    user_id = current_user.id_users
    
    # Pasar el user_id al repositorio
    top_products = product_repo.get_top_products(db, user_id)
    return top_products

@router.get("/", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def obtenemos_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los productos creados por el usuario autenticado."""
    productos = db.query(ProductsModel).filter(ProductsModel.owner_id == current_user.id_users).all()
    return [ProductsSchema.from_orm(producto) for producto in productos]

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


# @router.post("/", response_model=ProductsSchema, status_code=status.HTTP_201_CREATED)
# async def crear_producto_owner_image(
#     name: str = Form(...),
#     description: str = Form(...),
#     price: float = Form(...),
#     category_id: int = Form(...),
#     quantity: int = Form(...),
#     file: UploadFile = File(None),  # Hacer el archivo opcional
#     db: Session = Depends(get_db), 
#     current_user: User = Depends(get_current_user),
#     token: str = Depends(oauth2_scheme)
# ):
#     """Crea un nuevo producto asignando el owner_id del usuario autenticado, genera un pedido y detalle de pedido, y opcionalmente sube una imagen asociada."""
#     # 1. Validar la cantidad
#     if quantity <= 0:
#         raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que 0")

#     # 2. Crear el producto
#     db_product = ProductsModel(
#         name=name,
#         description=description,
#         price=price,
#         status="activo",  # Usar el valor por defecto de StatusEnum
#         category_id=category_id,
#         owner_id=current_user.id_users
#     )
#     db.add(db_product)
#     db.commit()
#     db.refresh(db_product)

#     # 3. Subir la imagen si se proporciona un archivo
#     if file:
#         try:
#             # Validar el tipo de archivo (solo imágenes)
#             if not file.content_type.startswith("image/"):
#                 raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

#             # Validar la extensión del archivo
#             allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}
#             file_extension = f".{file.filename.split('.')[-1].lower()}"
#             if file_extension not in allowed_extensions:
#                 raise HTTPException(status_code=400, detail="Solo se permiten imágenes con extensiones .jpg, .jpeg, .png o .gif")

#             # Generar un nombre único para el archivo
#             unique_filename = f"{uuid.uuid4()}{file_extension}"
#             file_path = UPLOAD_DIR / unique_filename

#             # Guardar el archivo en el sistema de archivos
#             with open(file_path, "wb") as buffer:
#                 content = await file.read()
#                 buffer.write(content)

#             # Crear el registro de la imagen en la base de datos
#             db_image = Image(
#                 file_name=unique_filename,
#                 file_path=str(file_path),
#                 user_id=current_user.id_users,
#                 product_id=db_product.id_products  # Asociar la imagen al producto recién creado
#             )
#             db.add(db_image)
#             db.commit()
#             db.refresh(db_image)
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

#     # 4. Crear un pedido (Orders) asociado al usuario autenticado
#     db_order = OrdersModel(
#         state="Ocupado",  # Estado inicial del pedido
#         date_time=datetime.utcnow(),
#         total=db_product.price * quantity,  # Total inicial basado en el precio del producto y la cantidad
#         orderscol="Orden creada automáticamente",
#         user_id=current_user.id_users,  # Asociar el pedido al usuario autenticado
#         product_name=db_product.name    # Tomar el nombre del producto
#     )
#     db.add(db_order)
#     db.commit()
#     db.refresh(db_order)

#     # 5. Crear un detalle de pedido (OrdersDetails) tomando datos de Products y Orders
#     unit_price = db_product.price  # Tomar el precio del producto
#     subtotal = quantity * unit_price  # Calcular el subtotal

#     db_order_detail = OrdersDetailsModel(
#         order_id=db_order.id_orders,  # Tomar el ID del pedido recién creado
#         product_id=db_product.id_products,  # Tomar el ID del producto recién creado
#         quantity=quantity,  # Usar la cantidad proporcionada en el formulario
#         unit_price=unit_price,  # Usar el precio del producto
#         subtotal=subtotal  # Calcular el subtotal
#     )
#     db.add(db_order_detail)
#     db.commit()
#     db.refresh(db_order_detail)

#     return ProductsSchema.from_orm(db_product)


# app/routers/products.py
@router.post("/",response_model=ProductsSchema,status_code=status.HTTP_201_CREATED,
    description="Crea un nuevo producto y opcionalmente sube una imagen asociada."
)
async def crear_producto_owner_image(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    quantity: int = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea un nuevo producto asignando el owner_id del usuario autenticado y opcionalmente sube una imagen asociada."""
    # 1. Validar la cantidad (aunque no se usará para crear órdenes aquí, se mantiene para validación)
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que 0")

    # 2. Crear el producto
    db_product = ProductsModel(
        name=name,
        description=description,
        price=price,
        status="activo",
        category_id=category_id,
        owner_id=current_user.id_users
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # 3. Subir la imagen si se proporciona un archivo
    if file:
        try:
            # Validar el tipo de archivo (solo imágenes)
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

            # Validar la extensión del archivo
            allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}
            file_extension = f".{file.filename.split('.')[-1].lower()}"
            if file_extension not in allowed_extensions:
                raise HTTPException(status_code=400, detail="Solo se permiten imágenes con extensiones .jpg, .jpeg, .png o .gif")

            # Generar un nombre único para el archivo
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = UPLOAD_DIR / unique_filename

            # Guardar el archivo en el sistema de archivos
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Crear el registro de la imagen en la base de datos
            db_image = Image(
                file_name=unique_filename,
                file_path=str(file_path),
                user_id=current_user.id_users,
                product_id=db_product.id_products
            )
            db.add(db_image)
            db.commit()
            db.refresh(db_image)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

    return ProductsSchema.from_orm(db_product)






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

