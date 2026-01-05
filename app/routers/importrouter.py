from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Products, Categoria, User, StatusEnum
from app.repository.auth import get_current_user
import pandas as pd
import io
import httpx 
import math
from app.schemas import AsignarRecetaSchema

router = APIRouter(
    prefix="/products",
    tags=["Products Import"],
)

# URL de tu microservicio (Ajustar a tu entorno real)
MICRO_URL = "https://api-micro.wapifood.com/inventory"


# --- FUNCIÓN NECESARIA PARA LIMPIAR DATOS ---
def clean_nan(val):
    """Convierte NaN de pandas a None o 0 según sea necesario"""
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


# ---------------------------------------------------------
# IMPORTAR INSUMOS (Corregido)
# ---------------------------------------------------------
@router.post("/insumos", status_code=status.HTTP_201_CREATED)
async def importar_insumos(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Lee Excel de Insumos y envía al Microservicio.
    """
    # 1. Validar extensión
    filename = file.filename.lower()
    if not filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(400, "Formato no soportado. Use .xlsx o .csv")

    # 2. Leer archivo
    contents = await file.read()
    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Error leyendo archivo: {e}")

    # 3. Normalizar columnas (Todo a minúsculas, sin espacios)
    df.columns = [str(c).lower().strip().replace(" ", "") for c in df.columns]
    # NOTA: Tu excel tiene "indicecliente" (sin espacio), así que .replace(" ", "") ayuda.

    payload_insumos = []
    errores = []

    for index, row in df.iterrows():
        try:
            # Validar nombre
            nombre = str(row.get('nombre', '')).strip()
            if not nombre or nombre.lower() == 'nan':
                continue 

            # CORRECCIÓN PRINCIPAL AQUÍ ABAJO:
            # Usamos current_user.email en lugar de current_user.username
            
            item = {
                "external_id": str(row.get('indicecliente', '')), 
                "name": nombre,
                "description": str(row.get('descripcion', '')),
                "stock_to_add": float(row.get('cantidad', 0) if clean_nan(row.get('cantidad')) is not None else 0),
                "cost": float(row.get('costo', 0) if clean_nan(row.get('costo')) is not None else 0),
                "unit": str(row.get('unidad', 'unidad')).strip(),
                "category": str(row.get('categoria', 'insumo')).strip(),
                
                # 🛠️ AQUÍ ESTABA EL ERROR: Tu modelo User usa 'email', no 'username'
                "username": current_user.email 
            }
            payload_insumos.append(item)

        except Exception as e:
            errores.append(f"Fila {index}: {str(e)}")

    if not payload_insumos:
        return {"message": "No se encontraron datos válidos", "errores": errores}

    # 4. Enviar al Microservicio
    # Necesitas pasar el token si tu microservicio requiere auth, o confiar en la red interna.
    # Si el microservicio es público/protegido, revisa los headers.
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{MICRO_URL}/internal/bulk-ingredients",
                json=payload_insumos,
                timeout=60.0
            )
            
            if response.status_code not in [200, 201]:
                 # Si falla el microservicio, mostramos qué pasó
                 return {
                     "message": "Error en Microservicio", 
                     "detalle_micro": response.text, 
                     "status": response.status_code
                 }
            
            return {
                "message": "Insumos enviados exitosamente",
                "stats_microservicio": response.json(),
                "errores_locales": errores
            }

        except httpx.RequestError as e:
            raise HTTPException(503, detail=f"No hay conexión con el Inventario: {e}")
        



# ---------------------------------------------------------
# IMPORTAR PRODUCTOS (Catálogo Local)
# ---------------------------------------------------------

@router.post("/productos", status_code=status.HTTP_201_CREATED)
async def importar_productos_flujo_completo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    1. Crea Producto Local.
    2. Envía datos al Microservicio para crear Ingrediente + Receta Automática (recipeStatusNoDisplay).
    """
    # --- 1. Lectura del Excel ---
    filename = file.filename.lower()
    contents = await file.read()
    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Error archivo: {e}")

    df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]

    # --- 2. Procesamiento Local ---
    payload_microservicio = []
    categorias_cache = {}
    productos_creados = 0

    for index, row in df.iterrows():
        try:
            nombre = str(row.get("nombre", "")).strip()
            if not nombre or nombre.lower() == 'nan': continue

            # Datos básicos
            cat_nombre = str(row.get("categoria", "General")).strip()
            precio = float(row.get("precio", 0) if clean_nan(row.get("precio")) is not None else 0)
            costo = float(row.get("costo_por_piezas", 0) if clean_nan(row.get("costo_por_piezas")) is not None else 0)
            # Asumimos que si es producto directo, la unidad es Pieza o lo que diga el excel
            unidad = str(row.get("unidad", "Piezas")).strip()
            cantidad_inicial = float(row.get("cantidad", 0) if clean_nan(row.get("cantidad")) is not None else 0)

            # A. Gestión Categoría Local
            cat_id = categorias_cache.get(cat_nombre)
            if not cat_id:
                cat_db = db.query(Categoria).filter(
                    Categoria.nombre_categoria == cat_nombre,
                    Categoria.owner_id == current_user.id_users
                ).first()
                if cat_db:
                    cat_id = cat_db.id_categoria
                else:
                    new_cat = Categoria(nombre_categoria=cat_nombre, owner_id=current_user.id_users, descripcion_categoria="Import", status="activo")
                    db.add(new_cat)
                    db.flush()
                    cat_id = new_cat.id_categoria
                categorias_cache[cat_nombre] = cat_id

            # B. Crear/Actualizar Producto Local
            producto = db.query(Products).filter(Products.name == nombre, Products.owner_id == current_user.id_users).first()
            
            if not producto:
                producto = Products(
                    name=nombre,
                    description=str(row.get("descripcion", "")),
                    price=precio,
                    production_cost=costo,
                    owner_id=current_user.id_users,
                    category_id=cat_id,
                    status=StatusEnum.activo
                )
                db.add(producto)
                db.flush() # NECESARIO para obtener producto.id_products
                productos_creados += 1
            else:
                # Si ya existe, actualizamos precios pero seguimos necesitando enviar al microservicio
                producto.price = precio
                producto.production_cost = costo

            # C. Preparar Payload para Microservicio
            # Aquí está la clave: enviamos ID local + Datos para ingrediente y receta
            payload_microservicio.append({
                "local_product_id": producto.id_products, # ID VINCULANTE
                "name": nombre,
                "cost": costo,
                "unit": unidad,
                "stock_to_add": cantidad_inicial,
                "username": current_user.email # O nombre, según tu auth
            })

        except Exception as e:
            print(f"Error fila {index}: {e}")
            continue

    db.commit()

    # --- 3. Enviar al Microservicio ---
    if payload_microservicio:
        async with httpx.AsyncClient() as client:
            try:
                # Llamamos a un endpoint NUEVO y ESPECÍFICO en el microservicio
                resp = await client.post(
                    f"{MICRO_URL}/internal/sync-product-flow",
                    json=payload_microservicio,
                    timeout=120.0 # Más tiempo porque hace muchas operaciones
                )
                if resp.status_code != 200:
                    return {"message": "Guardado local OK, pero error en sincronización Inventario", "error_micro": resp.text}
            except Exception as e:
                return {"message": "Guardado local OK, fallo conexión Microservicio", "error": str(e)}

    return {"message": "Proceso completado", "productos_locales": productos_creados}





@router.post("/productos/catalogo-simple", status_code=status.HTTP_201_CREATED)
async def importar_catalogo_simple(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PASO 1: Carga solo la información de venta.
    Columnas: nombre, precio, categoria, descripcion.
    """
    # 1. Leer Excel
    contents = await file.read()
    try:
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Error archivo: {e}")

    df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]

    productos_creados = []
    categorias_cache = {}

    for index, row in df.iterrows():
        try:
            nombre = str(row.get("nombre", "")).strip()
            if not nombre or nombre.lower() == 'nan': continue

            # --- Gestión Categoría ---
            cat_nombre = str(row.get("categoria", "General")).strip().upper()
            cat_id = categorias_cache.get(cat_nombre)
            
            if not cat_id:
                cat_db = db.query(Categoria).filter(
                    Categoria.nombre_categoria == cat_nombre, 
                    Categoria.owner_id == current_user.id_users
                ).first()
                if not cat_db:
                    new_cat = Categoria(nombre_categoria=cat_nombre, owner_id=current_user.id_users, descripcion_categoria="Import", status="activo")
                    db.add(new_cat)
                    db.flush()
                    cat_id = new_cat.id_categoria
                else:
                    cat_id = cat_db.id_categoria
                categorias_cache[cat_nombre] = cat_id

            # --- Crear Producto Local ---
            producto = db.query(Products).filter(
                Products.name == nombre, 
                Products.owner_id == current_user.id_users
            ).first()

            if not producto:
                producto = Products(
                    name=nombre,
                    description=str(row.get("descripcion", "")),
                    price=float(row.get("precio", 0)),
                    production_cost=0, # Se actualizará cuando asignen receta
                    owner_id=current_user.id_users,
                    category_id=cat_id,
                    status=StatusEnum.activo
                )
                db.add(producto)
                db.flush()
            
            # Guardamos info básica para responder al front
            productos_creados.append({
                "id": producto.id_products,
                "nombre": producto.name
            })

        except Exception as e:
            print(f"Error fila {index}: {e}")
            continue

    db.commit()
    return {"message": "Catálogo cargado", "productos": productos_creados}


@router.post("/productos/asignar-receta", status_code=200)
async def asignar_receta_manual(
    data: AsignarRecetaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recibe la selección del usuario (Match) y crea la receta en el Microservicio.
    """
    # 1. Validar que el producto exista y sea del usuario
    producto = db.query(Products).filter(
        Products.id_products == data.product_id,
        Products.owner_id == current_user.id_users
    ).first()

    if not producto:
        raise HTTPException(404, "Producto no encontrado o no te pertenece")

    # 2. Preparar payload para el Microservicio
    # Transformamos el esquema local al esquema que espera el microservicio
    payload_micro = {
        "local_product_id": producto.id_products,
        "product_name": producto.name,
        "username": current_user.email,
        "ingredients": [item.dict() for item in data.ingredients] # Lista de {ingredient_id, quantity}
    }

    # 3. Enviar al Microservicio
    # Usamos el endpoint que ya tenías para crear recetas complejas
    async with httpx.AsyncClient() as client:
        try:
            # OJO: El endpoint del microservicio espera una LISTA, así que enviamos [payload_micro]
            resp = await client.post(
                f"{MICRO_URL}/internal/sync-complex-recipes",
                json=[payload_micro], 
                timeout=20.0
            )
            
            if resp.status_code != 200:
                raise HTTPException(500, f"Error Microservicio: {resp.text}")
            
            # (Opcional) Si el microservicio devuelve el costo calculado, podrías actualizarlo aquí
            # producto.production_cost = resp.json()['stats']['costo_calculado']
            # db.commit()

            return {"message": "Receta asignada exitosamente", "micro_response": resp.json()}

        except Exception as e:
            raise HTTPException(503, f"Fallo conexión: {str(e)}")