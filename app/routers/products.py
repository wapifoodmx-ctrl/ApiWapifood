from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from typing import List, Annotated, Optional
from sqlalchemy.sql import func
from app.db.database import get_db
from app.db.models import Image, User, Products, OrdersDetails, Orders, ProductSelection
from app.schemas import ImageCreate, ImageResponse, TopProduct, ProductListInput
from app.db.models import Products as ProductsModel, Orders as OrdersModel, OrdersDetails as OrdersDetailsModel, User, Image as ImageModel
from app.schemas import Products as ProductsSchema, ProductsCreate, Orders as OrdersSchema, OrdersDetails as OrdersDetailsSchema
from app.oauth import get_current_user
from app.schemas import ProductUpdateSchema, TopProduct
from app.db.models import Categoria
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
from app.repository import products as product_repo



router = APIRouter(
        prefix="/products",
        tags=["Products"],
    )

# URL base del servidor para las imágenes
BASE_URL = "https://api.wapifood.com"
#BASE_URL = "http://localhost:8000"
#"https://api.wapifood.com"
# Directorio donde se guardarán las imágenes
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Esquema OAuth2 para el token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

# Mover esta ruta ANTES de las rutas dinámicas con {product_id}
@router.get("/top", status_code=status.HTTP_200_OK, response_model=List[TopProduct], description="Obtiene los productos más populares con su nombre, precio, unidades vendidas y subtotal.")
def get_top_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[TopProduct]:
    # Obtener el user_id del usuario autenticado
    user_id = current_user.id_users

    # Calcular las unidades vendidas por producto para el usuario autenticado
    top_products = (
        db.query(
            Products.name,
            Products.price,
            func.sum(OrdersDetails.quantity).label("units_sold"),
            func.sum(OrdersDetails.subtotal).label("subtotal")
        )
        .join(OrdersDetails, Products.id_products == OrdersDetails.product_id)
        .join(Orders, Orders.id_orders == OrdersDetails.order_id)
        .filter(Orders.user_id == user_id)
        .group_by(Products.id_products, Products.name, Products.price)
        .order_by(func.sum(OrdersDetails.quantity).desc())  # Ordenar por unidades vendidas de mayor a menor
        .limit(5)  # Limitar a los 5 más vendidos
        .all()
    )

    # Construir la lista de TopProduct con posiciones
    result = []
    for position, (name, price, units_sold, subtotal) in enumerate(top_products, 1):
        result.append(
            TopProduct(
                position=position,
                name=name,
                price=price,
                units_sold=units_sold,
                subtotal=subtotal
            )
        )
    return result


#-----------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------


# Ruta para obtener todos los productos del usuario autenticado (sin límite)
@router.get("/top", status_code=status.HTTP_200_OK, response_model=List[TopProduct], description="Obtiene todos los productos del usuario autenticado con su nombre, precio, unidades vendidas y subtotal, ordenados por unidades vendidas de mayor a menor.")
def get_all_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[TopProduct]:
    # Obtener el user_id del usuario autenticado
    user_id = current_user.id_users

    # Calcular las unidades vendidas por producto para el usuario autenticado
    all_products = (
        db.query(
            ProductsModel.name,
            ProductsModel.price,
            func.sum(OrdersDetailsModel.quantity).label("units_sold"),
            func.sum(OrdersDetailsModel.subtotal).label("subtotal")
        )
        .join(OrdersDetailsModel, ProductsModel.id_products == OrdersDetailsModel.product_id)
        .join(OrdersModel, OrdersModel.id_orders == OrdersDetailsModel.order_id)
        .filter(OrdersModel.user_id == user_id)
        .group_by(ProductsModel.id_products, ProductsModel.name, ProductsModel.price)
        .order_by(func.sum(OrdersDetailsModel.quantity).desc())  # Ordenar por unidades vendidas de mayor a menor
        .all()  # Sin limit(10) para devolver todos los productos
    )

    # Construir la lista de TopProduct con posiciones
    result = []
    for position, (name, price, units_sold, subtotal) in enumerate(all_products, 1):
        result.append(
            TopProduct(
                position=position,
                name=name,
                price=price,
                units_sold=units_sold,
                subtotal=subtotal
            )
        )
    return result


#-----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------




@router.get("/", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def obtenemos_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los productos creados por el usuario autenticado."""
    productos = (
        db.query(ProductsModel)
        .filter(ProductsModel.owner_id == current_user.id_users)
        .options(joinedload(ProductsModel.images))  # Cargar la relación images
        .options(joinedload(ProductsModel.category))  # Cargar la relación category
        .all()
    )

    if not productos:
        raise HTTPException(status_code=404, detail="No se encontraron productos para este usuario")

    # Convertir los productos a diccionarios y construir URLs completas para las imágenes
    productos_dicts = []
    for producto in productos:
        # Construir URLs completas usando el file_name de cada imagen
        image_urls = [
            f"{BASE_URL}/static/uploads/{image.file_name}"
            for image in producto.images
        ]
        producto_dict = {
            "id_products": producto.id_products,
            "name": producto.name,
            "description": producto.description,
            "price": producto.price,
            "category_id": producto.category_id,
            "status": producto.status,
            "image_url": image_urls,  # Usar URLs completas
            "nombre_categoria": producto.nombre_categoria,
            "production_cost": producto.production_cost  # Nuevo campo para costo de producción
        }
        productos_dicts.append(producto_dict)

    return [ProductsSchema.model_validate(producto_dict) for producto_dict in productos_dicts]





# 1. GET: Ver productos en la lista
@router.get("/custom-list", response_model=List[ProductsSchema], status_code=status.HTTP_200_OK)
def get_custom_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene SOLO los productos guardados en la lista de selección."""
    selection = (
        db.query(ProductsModel)
        .join(ProductSelection, ProductsModel.id_products == ProductSelection.product_id)
        .filter(ProductSelection.user_id == current_user.id_users)
        .options(joinedload(ProductsModel.images), joinedload(ProductsModel.category))
        .all()
    )

    products_dicts = []
    for producto in selection:
        # 1. Crear una copia limpia del diccionario del modelo
        p_dict = producto.__dict__.copy()
        
        # 2. ELIMINAR la clave interna de SQLAlchemy que causa el error 422
        if "_sa_instance_state" in p_dict:
            del p_dict["_sa_instance_state"]

        # 3. Construir URLs de imágenes
        image_urls = [f"{BASE_URL}/static/uploads/{image.file_name}" for image in producto.images]
        
        # 4. Actualizar el diccionario con los campos calculados
        p_dict["image_url"] = image_urls
        p_dict["nombre_categoria"] = producto.category.nombre_categoria if producto.category else None
        
        products_dicts.append(p_dict)

    return [ProductsSchema.model_validate(p) for p in products_dicts]



# 3. DELETE: Sacar productos de la lista
# CORRECCIÓN: Usamos @router.delete en lugar de @router.request
@router.delete("/custom-list", status_code=status.HTTP_200_OK)
def remove_from_custom_list(
    payload: ProductListInput, # { "product_ids": [10, 20] }
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saca productos de la lista de selección."""
    # Borramos solo de la tabla 'ProductSelection'
    deleted = db.query(ProductSelection).filter(
        ProductSelection.user_id == current_user.id_users,
        ProductSelection.product_id.in_(payload.product_ids)
    ).delete(synchronize_session=False)

    db.commit()
    return {"message": f"Se sacaron {deleted} productos de la lista."}


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
    file: UploadFile = File(None),
    production_cost: Optional[float] = Form(None),  # Nuevo campo opcional para costo de producción
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Crea un nuevo producto asignando el owner_id del usuario autenticado y opcionalmente sube una imagen asociada."""
    # 1. Validar la cantidad (aunque no se usará para crear órdenes aquí, se mantiene para validación)

    # 2. Crear el producto
    db_product = ProductsModel(
        name=name,
        description=description,
        price=price,
        status="activo",
        category_id=category_id,
        production_cost=production_cost,  # Asignar el costo de producción si se proporciona
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

#-----------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------




@router.patch("/{product_id}", response_model=ProductsSchema, status_code=status.HTTP_200_OK)
async def actualizar_producto(
    product_id: int,
    product_update: ProductUpdateSchema = Depends(),
    file: UploadFile = File(None),  # La imagen es opcional
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """
    Actualiza un producto existente si pertenece al usuario autenticado.
    Permite actualizar:
    - Solo la imagen.
    - Solo otros campos (name, description, price, status, category_id).
    - La imagen y otros campos.
    - Cualquier combinación de campos.
    Los campos no proporcionados no se modifican.
    """
    # Depuración: Imprimir los datos recibidos
    print(f"Datos recibidos: product_id={product_id}, update={product_update.dict()}, "
          f"file={file.filename if file else None}, user_id={current_user.id_users}")

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
    
    try:
        # Guardar los valores actuales del producto para comparar después
        original_values = {
            "name": db_product.name,
            "description": db_product.description,
            "price": db_product.price,
            "status": db_product.status,
            "category_id": db_product.category_id,
            "production_cost": db_product.production_cost  # Nuevo campo para costo de producción
        }
        print(f"Valores originales del producto: {original_values}")

        # Caso 1: Actualizar los campos del producto (si se proporcionan)
        # Solo se actualizan los campos que no sean None
        updated_fields = []
        if product_update.name is not None:
            updated_fields.append(f"name={product_update.name}")
            db_product.name = product_update.name
        if product_update.description is not None:
            updated_fields.append(f"description={product_update.description}")
            db_product.description = product_update.description

        if product_update.production_cost is not None:
            if product_update.production_cost < 0:  # Validación opcional para evitar costos negativos
                raise HTTPException(
            status_code=400,
            detail="El costo de producción no puede ser negativo"
                )
            updated_fields.append(f"production_cost={product_update.production_cost}")
            db_product.production_cost = product_update.production_cost


        if product_update.price is not None:
            updated_fields.append(f"price={product_update.price}")
            db_product.price = product_update.price
        if product_update.status is not None:
            allowed_statuses = ["activo", "inactivo"]
            if product_update.status not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"El status debe ser uno de {allowed_statuses}"
                )
            updated_fields.append(f"status={product_update.status}")
            db_product.status = product_update.status
        if product_update.category_id is not None:
            # Validar que la categoría exista
            category = db.query(Categoria).filter(Categoria.id_categoria == product_update.category_id).first()
            if not category:
                raise HTTPException(
                    status_code=400,
                    detail=f"Categoría con ID {product_update.category_id} no encontrada"
                )
            updated_fields.append(f"category_id={product_update.category_id}")
            db_product.category_id = product_update.category_id

        if updated_fields:
            print(f"Campos actualizados del producto: {updated_fields}")
        else:
            print("No se proporcionaron campos para actualizar el producto.")

        # Caso 2: Actualizar la imagen (si se proporciona un archivo)
        if file:
            print(f"Procesando nueva imagen: {file.filename}")
            try:
                # Validar el tipo de archivo (solo imágenes)
                if not file.content_type.startswith("image/"):
                    raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

                # Validar la extensión del archivo
                allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}
                file_extension = f".{file.filename.split('.')[-1].lower()}"
                if file_extension not in allowed_extensions:
                    raise HTTPException(status_code=400, detail="Solo se permiten imágenes con extensiones .jpg, .jpeg, .png o .gif")

                # Buscar la imagen existente asociada al producto (si existe)
                existing_image = db.query(Image).filter(Image.product_id == product_id).first()
                if existing_image:
                    print(f"Eliminando imagen existente: {existing_image.file_path}")
                    # Eliminar el archivo físico del sistema de archivos
                    old_file_path = Path(existing_image.file_path)
                    if old_file_path.exists():
                        old_file_path.unlink()  # Elimina el archivo anterior
                    # Eliminar el registro de la imagen de la base de datos
                    db.delete(existing_image)
                    db.commit()  # Commit intermedio para asegurar que la imagen anterior se elimine

                # Generar un nombre único para el nuevo archivo
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = UPLOAD_DIR / unique_filename

                # Guardar el nuevo archivo en el sistema de archivos
                print(f"Guardando nueva imagen en: {file_path}")
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)

                # Crear un nuevo registro de imagen en la base de datos
                print(f"Creando nuevo registro de imagen para product_id={product_id}")
                db_image = Image(
                    file_name=unique_filename,
                    file_path=str(file_path),
                    user_id=current_user.id_users,
                    product_id=db_product.id_products
                )
                db.add(db_image)
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")
        else:
            print("No se proporcionó una nueva imagen para actualizar.")

        # Caso 3: Verificar si se hizo alguna actualización
        if not updated_fields and not file:
            print("No se proporcionaron campos ni imagen para actualizar. No se realizarán cambios.")
            return ProductsSchema.from_orm(db_product)

        # Confirmar todos los cambios
        print("Confirmando cambios en la base de datos...")
        db.commit()
        db.refresh(db_product)
        print("Cambios confirmados exitosamente")

        # Verificar los valores después de la actualización
        updated_values = {
            "name": db_product.name,
            "description": db_product.description,
            "price": db_product.price,
            "status": db_product.status,
            "category_id": db_product.category_id, 
            "production_cost": db_product.production_cost  # Nuevo campo para costo de producción
        }
        print(f"Valores después de la actualización: {updated_values}")

    except Exception as e:
        db.rollback()
        print(f"Error al confirmar cambios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al actualizar el producto: {str(e)}")

    return ProductsSchema.from_orm(db_product)




#---------------------------------------------------------------------------------------------

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


# ==========================================
# 📋 ENDPOINTS DE LISTA DE SELECCIÓN (CUSTOM LIST)
# ==========================================



# 2. POST: Agregar productos a la lista (Sin duplicados)
@router.post("/custom-list", status_code=status.HTTP_201_CREATED)
def add_to_custom_list(
    payload: ProductListInput, # { "product_ids": [10, 20] }
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mete productos a la lista de selección."""
    added_count = 0
    
    for pid in payload.product_ids:
        # Verificar que el producto exista y sea del usuario (Seguridad)
        product = db.query(ProductsModel).filter(
            ProductsModel.id_products == pid, 
            ProductsModel.owner_id == current_user.id_users
        ).first()
        
        if not product: continue # Si no es mío o no existe, lo salto

        # Verificar si ya está en la lista para no repetir
        exists = db.query(ProductSelection).filter(
            ProductSelection.user_id == current_user.id_users,
            ProductSelection.product_id == pid
        ).first()

        if not exists:
            new_selection = ProductSelection(
                user_id=current_user.id_users,
                product_id=pid
            )
            db.add(new_selection)
            added_count += 1
            
    db.commit()
    return {"message": f"Se agregaron {added_count} productos a la lista."}


