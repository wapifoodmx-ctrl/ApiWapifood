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
    Lee Excel, convierte Kilos->Gramos y Litros->Mililitros, y envía al Microservicio.
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

    # 3. Normalizar columnas
    df.columns = [str(c).lower().strip().replace(" ", "") for c in df.columns]

    payload_insumos = []
    errores = []

    for index, row in df.iterrows():
        try:
            nombre = str(row.get('nombre', '')).strip()
            if not nombre or nombre.lower() == 'nan':
                continue 

            # --- LECTURA DE DATOS CRUDOS ---
            raw_unidad = str(row.get('unidad', 'unidad')).strip()
            raw_cantidad = float(row.get('cantidad', 0) if clean_nan(row.get('cantidad')) is not None else 0)
            raw_costo = float(row.get('costo', 0) if clean_nan(row.get('costo')) is not None else 0)

            # --- 🧠 LÓGICA DE CONVERSIÓN (Kilos -> Gramos / Litros -> Mililitros) ---
            final_unidad = raw_unidad
            final_cantidad = raw_cantidad
            final_costo = raw_costo
            
            unidad_lower = raw_unidad.lower()

            # CASO 1: KILOS -> GRAMOS
            if unidad_lower in ['kilos', 'kilo', 'kg', 'kgs']:
                final_unidad = "Gramos"
                final_cantidad = raw_cantidad * 1000  # 20 Kg -> 20,000 gr
                if raw_costo > 0:
                    final_costo = raw_costo / 1000    # $100 el Kg -> $0.10 el gramo

            # CASO 2: LITROS -> MILILITROS
            elif unidad_lower in ['litros', 'litro', 'l', 'lt', 'lts']:
                final_unidad = "Mililitros"
                final_cantidad = raw_cantidad * 1000  # 5 L -> 5,000 ml
                if raw_costo > 0:
                    final_costo = raw_costo / 1000    # $50 el Litro -> $0.05 el ml

            # -----------------------------------------------------------------------

            item = {
                "external_id": str(row.get('indicecliente', '')), 
                "name": nombre,
                "description": str(row.get('descripcion', '')),
                "stock_to_add": final_cantidad, # Enviamos la cantidad convertida
                "cost": final_costo,            # Enviamos el costo unitario (por gramo/ml)
                "unit": final_unidad,           # Enviamos la nueva unidad estandarizada
                "category": str(row.get('categoria', 'insumo')).strip(),
                "username": current_user.email 
            }
            payload_insumos.append(item)

        except Exception as e:
            errores.append(f"Fila {index}: {str(e)}")

    if not payload_insumos:
        return {"message": "No se encontraron datos válidos", "errores": errores}

    # 4. Enviar al Microservicio
    # Desactivamos la verificación SSL para evitar el error de certificado
    async with httpx.AsyncClient(verify=False) as client: 
        try:
            response = await client.post(
                f"{MICRO_URL}/internal/bulk-ingredients",
                json=payload_insumos,
                timeout=60.0
            )
            
            if response.status_code not in [200, 201]:
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
            cat_nombre = str(row.get("categoria", "General")).strip().upper()
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
        async with httpx.AsyncClient(verify=False) as client:
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




# En APIWAPI (routers/importacion.py)

@router.post("/productos/carga-completa-recetas", status_code=status.HTTP_201_CREATED)
async def importar_productos_con_receta_completa(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Carga masiva de Productos + Recetas.
    El Excel debe tener los IDs de los ingredientes ya existentes.
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

    payload_recetas = []
    productos_creados = 0
    errores = []
    categorias_cache = {}

    for index, row in df.iterrows():
        try:
            nombre = str(row.get("nombre", "")).strip()
            if not nombre or nombre.lower() == 'nan': continue

            # --- A. Crear Producto Local ---
            cat_nombre = str(row.get("categoria", "General")).strip().upper()
            cat_id = categorias_cache.get(cat_nombre)
            
            if not cat_id:
                # (Lógica de crear categoría si no existe - Igual que antes)
                cat_db = db.query(Categoria).filter(Categoria.nombre_categoria == cat_nombre, Categoria.owner_id == current_user.id_users).first()
                if not cat_db:
                    new_cat = Categoria(nombre_categoria=cat_nombre, owner_id=current_user.id_users, descripcion_categoria="Import", status="activo")
                    db.add(new_cat); db.flush()
                    cat_id = new_cat.id_categoria
                else:
                    cat_id = cat_db.id_categoria
                categorias_cache[cat_nombre] = cat_id

            producto = db.query(Products).filter(Products.name == nombre, Products.owner_id == current_user.id_users).first()
            if not producto:
                producto = Products(
                    name=nombre,
                    description=str(row.get("descripcion", "")),
                    price=float(row.get("precio", 0)),
                    production_cost=0, 
                    owner_id=current_user.id_users,
                    category_id=cat_id,
                    status=StatusEnum.activo
                )
                db.add(producto)
                db.flush() # Obtener ID
                productos_creados += 1
            
            # --- B. Procesar Receta (IDs y Cantidades) ---
            # Leemos las columnas 'ids_insumos' y 'cantidades' (ej: "75,74" y "1,1")
            ids_raw = str(row.get("ids_insumos", ""))
            cantidades_raw = str(row.get("cantidades", "")) # Puede llamarse 'cantidades_de_los_ingredientes...' en tu excel

            # Limpieza básica
            if ids_raw and ids_raw.lower() != 'nan' and cantidades_raw and cantidades_raw.lower() != 'nan':
                lista_ids = [x.strip() for x in ids_raw.split(',') if x.strip()]
                lista_cantidades = [x.strip() for x in cantidades_raw.split(',') if x.strip()]

                if len(lista_ids) == len(lista_cantidades):
                    ingredientes_data = []
                    for i in range(len(lista_ids)):
                        try:
                            ing_id = int(float(lista_ids[i])) # Convertir a int (por si viene como 75.0)
                            qty = float(lista_cantidades[i])
                            ingredientes_data.append({"ingredient_id": ing_id, "quantity": qty})
                        except ValueError:
                            pass # Ignorar valores no numéricos
                    
                    if ingredientes_data:
                        payload_recetas.append({
                            "local_product_id": producto.id_products,
                            "product_name": producto.name,
                            "username": current_user.email,
                            "ingredients": ingredientes_data
                        })
                else:
                    errores.append(f"Fila {index}: La cantidad de IDs no coincide con la cantidad de montos.")

        except Exception as e:
            errores.append(f"Fila {index}: {str(e)}")

    db.commit()

    # --- C. Enviar Recetas al Microservicio ---
    if payload_recetas:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{MICRO_URL}/internal/sync-complex-recipes",
                    json=payload_recetas,
                    timeout=60.0
                )
                if resp.status_code != 200:
                    return {"message": "Productos creados, error en recetas", "detalle": resp.text}
            except Exception as e:
                return {"message": "Productos creados, fallo conexión microservicio", "error": str(e)}

    return {
        "message": "Carga completa", 
        "productos_creados": productos_creados, 
        "recetas_enviadas": len(payload_recetas),
        "errores": errores
    }


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
    async with httpx.AsyncClient(verify=False) as client:
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