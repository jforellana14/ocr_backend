import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

import cloudinary
import cloudinary.uploader
import tempfile
from urllib.parse import urlparse
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database_init import initialize_database
from app.pricing.engine import PricingEngine
from app.routers import (expense_categories, expenses, finance, fuel_price_sync, rate_plan_details,
                         rate_plans, reports, tariff_excel_import, tariff_import)
from auth import create_token, get_current_user, hash_password, require_roles, verify_password
from database import get_db
from models import (Base, ChargeType, Client, Document, FinancialSettings, FuelPrice,
                    Pilot, Route, Truck, User, VehicleType)
from schemas import (ChargeTypeCreate, ChargeTypeResponse, ClientCreate, ClientResponse,
                     DocumentResponse, DocumentUpdate, FinancialSettingsCreate,
                     FinancialSettingsResponse, FuelPriceCreate, FuelPriceResponse,
                     LoginRequest, PilotCreate, PilotResponse, RouteCreate, RouteResponse,
                     TruckCreate, TruckResponse, UserCreate, UserResponse, UserUpdate, UserPasswordUpdate,
                     VehicleTypeCreate, VehicleTypeResponse)

initialize_database()

app = FastAPI(title="Transportes JDA ERP API", version="3.0.0")
for router in (rate_plans.router, rate_plan_details.router, expense_categories.router,
               expenses.router, finance.router, reports.router, tariff_import.router,
               tariff_excel_import.router, fuel_price_sync.router):
    app.include_router(router)

cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
allow_all_origins = cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"),
                  api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "OCR Backend Running"}
    

@app.get("/pilots/filter")
def get_pilots_filter(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(Document.piloto)
        .filter(Document.piloto.isnot(None), Document.piloto != "")
        .distinct()
        .order_by(Document.piloto.asc())
        .all()
    )
    return [row[0] for row in rows]

@app.get("/documents", response_model=list[DocumentResponse])
def get_documents(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    piloto: Optional[str] = Query(None),
    origen: Optional[str] = Query(None),
    destino: Optional[str] = Query(None),
    producto: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = db.query(Document)

    if current_user.role == "PILOTO":
        query = query.filter(
            Document.created_by_user_id == current_user.id
        )

    if fecha_desde:
        query = query.filter(Document.fecha >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Document.fecha <= fecha_hasta)

    if piloto:
        query = query.filter(
            Document.piloto.ilike(f"%{piloto}%")
        )

    if origen:
        query = query.filter(
            Document.origen.ilike(f"%{origen}%")
        )

    if destino:
        query = query.filter(
            Document.destino.ilike(f"%{destino}%")
        )

    if producto:
        query = query.filter(
            Document.producto.ilike(f"%{producto}%")
        )

    sort_column = getattr(
        Document,
        sort_by,
        Document.created_at
    )

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    return query.all()


@app.post("/pilots", response_model=PilotResponse)
def create_pilot(
    pilot: PilotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO")),
):
    nombre = pilot.nombre.upper().strip()

    existing = db.query(Pilot).filter(Pilot.nombre == nombre).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Pilot already exists"
        )

    new_pilot = Pilot(
        nombre=nombre,
        activo="SI"
    )

    db.add(new_pilot)
    db.commit()
    db.refresh(new_pilot)

    return new_pilot

@app.put("/pilots/{pilot_id}", response_model=PilotResponse)
def update_pilot(
    pilot_id: int,
    pilot: PilotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO")),
):
    existing = db.query(Pilot).filter(Pilot.id == pilot_id).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Pilot not found")

    new_name = pilot.nombre.upper().strip()
    duplicate = (
        db.query(Pilot)
        .filter(Pilot.nombre == new_name, Pilot.id != pilot_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Pilot already exists")

    existing.nombre = new_name

    db.commit()
    db.refresh(existing)

    return existing

@app.get("/pilots", response_model=list[PilotResponse])
def get_pilots(db: Session = Depends(get_db)):
    return (
        db.query(Pilot)
        .filter(Pilot.activo == "SI")
        .order_by(Pilot.nombre.asc())
        .all()
    )


@app.delete("/pilots/{pilot_id}")
def delete_pilot(
    pilot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO")),
):
    pilot = db.query(Pilot).filter(Pilot.id == pilot_id).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    pilot.activo = "NO"

    db.commit()

    return {"message": "Pilot disabled successfully"}

@app.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "PILOTO":
        raise HTTPException(
            status_code=403,
            detail="Pilots cannot edit documents"
        )

    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    data = payload.dict(exclude_unset=True)

    # =====================================================
    # VALIDAR PRECIO DE COMBUSTIBLE
    # =====================================================

    if "fuel_price" in data:
        fuel_price = data["fuel_price"]

        if fuel_price is not None:
            try:
                fuel_price = float(fuel_price)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid fuel price"
                )

            if fuel_price < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Fuel price cannot be negative"
                )

            data["fuel_price"] = fuel_price

            # Si el precio fue ingresado manualmente,
            # deja de estar asociado a un registro automático.
            data["fuel_price_id"] = None

    # =====================================================
    # ACTUALIZAR CAMPOS
    # =====================================================

    for key, value in data.items():

        if isinstance(value, str):
            setattr(document, key, value.upper())
        else:
            setattr(document, key, value)

    try:
        db.commit()
        db.refresh(document)

    except Exception as e:
        db.rollback()

        print(
            "ERROR actualizando documento:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Error updating document"
        )

    return document

@app.put("/documents/{document_id}/image", response_model=DocumentResponse)
async def replace_document_image(
    document_id: int,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "PILOTO":
        raise HTTPException(
            status_code=403,
            detail="Pilots cannot edit documents"
        )

    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # =====================================================
    # VALIDAR IMAGEN
    # =====================================================

    allowed_types = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp"
    }

    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format"
        )

    old_image_url = document.image_path
    new_image_url = None
    new_public_id = None
    temp_path = None

    try:

        # =================================================
        # GUARDAR ARCHIVO TEMPORAL
        # =================================================

        suffix = os.path.splitext(
            image.filename or ""
        )[1]

        if not suffix:
            suffix = ".jpg"

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            content = await image.read()

            if not content:
                raise HTTPException(
                    status_code=400,
                    detail="Empty image"
                )

            temp_file.write(content)

            temp_path = temp_file.name

        # =================================================
        # SUBIR NUEVA IMAGEN A CLOUDINARY
        # =================================================

        print(
            "Subiendo nueva imagen de boleta a Cloudinary..."
        )

        upload_result = cloudinary.uploader.upload(
            temp_path,
            folder="ordenes_boletas",
            resource_type="image"
        )

        new_image_url = upload_result.get("secure_url")
        new_public_id = upload_result.get("public_id")

        if not new_image_url or not new_public_id:
            raise Exception(
                "Cloudinary did not return secure_url/public_id"
            )

        print(
            "Nueva imagen Cloudinary:",
            new_public_id
        )

        # =================================================
        # ACTUALIZAR BD
        # =================================================

        document.image_path = new_image_url

        db.commit()
        db.refresh(document)

        # =================================================
        # ELIMINAR IMAGEN ANTERIOR
        #
        # Se hace DESPUÉS de:
        # 1. subir nueva imagen
        # 2. guardar nueva URL en PostgreSQL
        # =================================================

        if (
            old_image_url
            and "res.cloudinary.com" in old_image_url
            and old_image_url != new_image_url
        ):

            try:

                parsed_url = urlparse(old_image_url)
                path = parsed_url.path

                if "/upload/" not in path:
                    raise Exception(
                        "Could not determine old Cloudinary public_id"
                    )

                cloudinary_path = path.split(
                    "/upload/",
                    1
                )[1]

                partes = cloudinary_path.split("/")

                # Quitar versión v123456
                if (
                    partes
                    and partes[0].startswith("v")
                    and partes[0][1:].isdigit()
                ):
                    partes = partes[1:]

                cloudinary_path = "/".join(partes)

                # Quitar extensión
                old_public_id = cloudinary_path.rsplit(
                    ".",
                    1
                )[0]

                print(
                    "Eliminando imagen anterior:",
                    old_public_id
                )

                resultado = cloudinary.uploader.destroy(
                    old_public_id,
                    resource_type="image",
                    invalidate=True
                )

                print(
                    "Resultado eliminación:",
                    resultado
                )

                cloudinary_result = resultado.get("result")

                if cloudinary_result not in (
                    "ok",
                    "not found"
                ):
                    raise Exception(
                        "Cloudinary did not confirm deletion "
                        f"of old image: {resultado}"
                    )

            except Exception as e:

                # La nueva imagen YA está guardada.
                # No borramos la boleta ni revertimos
                # a una URL que podría quedar inconsistente.
                print(
                    "ADVERTENCIA: nueva imagen guardada, "
                    "pero no se pudo eliminar la anterior:",
                    str(e)
                )

        return document

    except HTTPException:

        db.rollback()

        # Si ya subimos la nueva imagen pero PostgreSQL falló,
        # intentar eliminarla para no dejarla huérfana.
        if new_public_id:

            try:
                cloudinary.uploader.destroy(
                    new_public_id,
                    resource_type="image",
                    invalidate=True
                )
            except Exception:
                pass

        raise

    except Exception as e:

        db.rollback()

        # =================================================
        # LIMPIAR NUEVA IMAGEN SI ALGO FALLÓ
        # =================================================

        if new_public_id:

            try:

                cloudinary.uploader.destroy(
                    new_public_id,
                    resource_type="image",
                    invalidate=True
                )

            except Exception as cleanup_error:

                print(
                    "ERROR limpiando nueva imagen:",
                    str(cleanup_error)
                )

        print(
            "ERROR reemplazando imagen:",
            str(e)
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Could not replace document image. "
                "Original image was preserved."
            )
        )

    finally:

        # =================================================
        # BORRAR ARCHIVO TEMPORAL
        # =================================================

        if temp_path and os.path.exists(temp_path):

            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "PILOTO":
        raise HTTPException(
            status_code=403,
            detail="Pilots cannot delete documents"
        )

    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # =====================================================
    # ELIMINAR IMAGEN DE CLOUDINARY
    # =====================================================

    if document.image_path:

        image_url = document.image_path

        # Solo procesar como Cloudinary si la URL pertenece a Cloudinary
        if "res.cloudinary.com" in image_url:

            try:
                parsed_url = urlparse(image_url)
                path = parsed_url.path

                if "/upload/" not in path:
                    raise HTTPException(
                        status_code=500,
                        detail="Could not determine Cloudinary public_id"
                    )

                # Ejemplo:
                # v123456/ordenes_boletas/imagen.jpg
                cloudinary_path = path.split("/upload/", 1)[1]

                partes = cloudinary_path.split("/")

                # Quitar versión v123456
                if (
                    partes
                    and partes[0].startswith("v")
                    and partes[0][1:].isdigit()
                ):
                    partes = partes[1:]

                cloudinary_path = "/".join(partes)

                # Quitar extensión
                public_id = cloudinary_path.rsplit(".", 1)[0]

                print(
                    f"Eliminando imagen Cloudinary: {public_id}"
                )

                resultado = cloudinary.uploader.destroy(
                    public_id,
                    resource_type="image",
                    invalidate=True
                )

                print(
                    f"Resultado Cloudinary: {resultado}"
                )

                cloudinary_result = resultado.get("result")

                # =============================================
                # RESULTADOS ACEPTADOS
                # =============================================

                # "ok" = imagen eliminada correctamente
                #
                # "not found" = imagen ya no existe.
                # Permitimos eliminar la boleta porque no
                # quedará una imagen huérfana.

                if cloudinary_result not in ("ok", "not found"):

                    print(
                        "Cloudinary no confirmó eliminación:",
                        resultado
                    )

                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Cloudinary could not delete the image. "
                            "Document was NOT deleted."
                        )
                    )

            except HTTPException:
                # Importante:
                # No continuar con db.delete()
                raise

            except Exception as e:

                print(
                    "ERROR eliminando imagen de Cloudinary:",
                    str(e)
                )

                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Error deleting image from Cloudinary. "
                        "Document was NOT deleted. "
                        f"Error: {str(e)}"
                    )
                )

    # =====================================================
    # ELIMINAR REGISTRO DE BASE DE DATOS
    #
    # Solo llegamos aquí si:
    #
    # 1. No había imagen
    # 2. No era una URL Cloudinary
    # 3. Cloudinary respondió "ok"
    # 4. Cloudinary respondió "not found"
    # =====================================================

    try:

        db.delete(document)
        db.commit()

    except Exception as e:

        db.rollback()

        print(
            "ERROR eliminando documento de BD:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Error deleting document from database"
        )

    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }

@app.post("/documents/manual", response_model=DocumentResponse)
async def create_manual_document(
    fecha: str = Form(""),
    origen: str = Form(""),
    destino: str = Form(""),
    producto: str = Form(""),
    piloto: str = Form(""),
    no_orden_carga: str = Form(""),
    peso_entregado: str = Form(""),
    no_constancia_viaje: str = Form(""),
    combustible_consumido: float = Form(0),
    no_vale: str = Form(""),
    cliente_id: int | None = Form(None),
    truck_id: int | None = Form(None),
    route_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    temp_dir = "temp_uploads"
    temp_file_path = None

    try:
        # ============================================================
        # 1. NORMALIZAR DATOS
        # ============================================================

        fecha_original = (fecha or "").strip()
        origen_original = (origen or "").strip()
        destino_original = (destino or "").strip()

        producto = (producto or "").strip()
        piloto = (piloto or "").strip()
        no_orden_carga = (no_orden_carga or "").strip()
        peso_entregado = (peso_entregado or "").strip()
        no_constancia_viaje = (
            no_constancia_viaje or ""
        ).strip()
        no_vale = (no_vale or "").strip()

        # ============================================================
        # 2. FECHA
        # Soporta Web YYYY-MM-DD y Android DD/MM/YYYY
        # ============================================================

        if not fecha_original:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar la fecha del viaje.",
            )

        pricing_date = None

        for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                pricing_date = datetime.strptime(
                    fecha_original[:10],
                    date_format,
                ).date()
                break
            except ValueError:
                continue

        if pricing_date is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Formato de fecha inválido: {fecha_original}. "
                    "Use YYYY-MM-DD o DD/MM/YYYY."
                ),
            )

        fecha_normalizada = pricing_date.strftime("%Y-%m-%d")

        # ============================================================
        # 3. PESO
        # ============================================================

        if not peso_entregado:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar los quintales entregados.",
            )

        try:
            peso_numerico = float(
                peso_entregado.replace(",", ".")
            )
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Peso entregado inválido: {peso_entregado}"
                ),
            )

        if peso_numerico <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "El peso entregado debe ser mayor que cero."
                ),
            )

        # ============================================================
        # 4. PILOTO
        # ============================================================

        final_piloto = piloto.upper().strip()

        if current_user.role == "PILOTO":
            if not current_user.piloto_nombre:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "El usuario piloto no tiene "
                        "un piloto asociado."
                    ),
                )

            final_piloto = (
                current_user.piloto_nombre
                .upper()
                .strip()
            )

        if not final_piloto:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar el piloto.",
            )

        # ============================================================
        # 5. ORIGEN / DESTINO
        # ============================================================

        origen_busqueda = " ".join(
            origen_original.upper().split()
        )

        destino_busqueda = " ".join(
            destino_original.upper().split()
        )

        if not origen_busqueda:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar el origen.",
            )

        if not destino_busqueda:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar el destino.",
            )

        # ============================================================
        # 6. BUSCAR RUTA
        #
        # IMPORTANTE:
        # La inexistencia de la ruta YA NO bloquea la boleta.
        # ============================================================

        route = None

        if route_id is not None:
            route = (
                db.query(Route)
                .filter(Route.id == route_id)
                .first()
            )

            if not route:
                print(
                    f"WARNING: route_id={route_id} no existe. "
                    "La boleta se guardará pendiente."
                )

                route_id = None

        if route is None:
            # --------------------------------------------------------
            # Coincidencia exacta
            # --------------------------------------------------------

            rutas = (
                db.query(Route)
                .filter(
                    func.upper(func.trim(Route.origen))
                    == origen_busqueda,
                    func.upper(func.trim(Route.destino))
                    == destino_busqueda,
                )
                .all()
            )

            # --------------------------------------------------------
            # Coincidencia compatible
            # --------------------------------------------------------

            if not rutas:
                todas_las_rutas = db.query(Route).all()

                coincidencias = []

                for candidate in todas_las_rutas:
                    candidate_origen = " ".join(
                        (
                            candidate.origen or ""
                        )
                        .strip()
                        .upper()
                        .split()
                    )

                    candidate_destino = " ".join(
                        (
                            candidate.destino or ""
                        )
                        .strip()
                        .upper()
                        .split()
                    )

                    if (
                        not candidate_origen
                        or not candidate_destino
                    ):
                        continue

                    origen_coincide = (
                        origen_busqueda == candidate_origen
                        or origen_busqueda in candidate_origen
                        or candidate_origen in origen_busqueda
                    )

                    destino_coincide = (
                        destino_busqueda == candidate_destino
                        or destino_busqueda in candidate_destino
                        or candidate_destino in destino_busqueda
                    )

                    if (
                        origen_coincide
                        and destino_coincide
                    ):
                        coincidencias.append(candidate)

                rutas = coincidencias

            # --------------------------------------------------------
            # Solo usar automáticamente si existe UNA coincidencia
            # --------------------------------------------------------

            if len(rutas) == 1:
                route = rutas[0]
                route_id = route.id

                print(
                    "RUTA ENCONTRADA:",
                    route.id,
                    route.origen,
                    "->",
                    route.destino,
                )

            elif len(rutas) > 1:
                # No escoger al azar.
                route = None
                route_id = None

                print(
                    "WARNING: múltiples rutas compatibles. "
                    "La boleta se guardará pendiente:",
                    [
                        (
                            r.id,
                            r.origen,
                            r.destino,
                        )
                        for r in rutas
                    ],
                )

            else:
                route = None
                route_id = None

                print(
                    "RUTA NUEVA / NO CONFIGURADA:",
                    origen_busqueda,
                    "->",
                    destino_busqueda,
                    "| boleta se guardará pendiente",
                )

        # ============================================================
        # 7. ORIGEN / DESTINO FINALES
        # ============================================================

        if route is not None:
            origen_final = (
                route.origen
                or origen_original
            ).strip().upper()

            destino_final = (
                route.destino
                or destino_original
            ).strip().upper()

        else:
            # Conservamos exactamente la operación capturada
            # por Android.
            origen_final = origen_busqueda
            destino_final = destino_busqueda

        # ============================================================
        # 8. PRICING
        #
        # Valores por defecto = viaje pendiente de tarifar.
        # ============================================================

        pricing = None

        fuel_price_id = None
        fuel_price = None

        rate_plan_id = None
        rate_plan_detail_id = None

        precio_unitario = None
        precio_total = None
        bonificacion_piloto = None

        pricing_version = 1

        # Solo intentar pricing cuando conocemos la ruta.
        if route_id is not None:
            try:
                pricing = PricingEngine.calculate_for_route(
                    db=db,
                    fecha=pricing_date,
                    route_id=route_id,
                    client_id=cliente_id,
                    peso=peso_numerico,
                )

                if pricing is not None:
                    fuel_price_id = getattr(
                        pricing,
                        "fuel_price_id",
                        None,
                    )

                    fuel_price = getattr(
                        pricing,
                        "fuel_price",
                        None,
                    )

                    rate_plan_id = getattr(
                        pricing,
                        "rate_plan_id",
                        None,
                    )

                    rate_plan_detail_id = getattr(
                        pricing,
                        "rate_plan_detail_id",
                        None,
                    )

                    precio_unitario = getattr(
                        pricing,
                        "precio_unitario",
                        None,
                    )

                    precio_total = getattr(
                        pricing,
                        "precio_total",
                        None,
                    )

                    bonificacion_piloto = getattr(
                        pricing,
                        "bonificacion",
                        None,
                    )

                    pricing_version = (
                        getattr(
                            pricing,
                            "version",
                            1,
                        )
                        or 1
                    )

                    print(
                        "PRICING OK:",
                        "route_id=",
                        route_id,
                        "precio_total=",
                        precio_total,
                    )

            except Exception as pricing_error:
                # ====================================================
                # IMPORTANTE:
                # Un error de pricing YA NO bloquea la operación.
                # La boleta se guarda pendiente.
                # ====================================================

                print(
                    "PRICING PENDIENTE:",
                    type(pricing_error).__name__,
                    str(pricing_error),
                )

                pricing = None

                fuel_price_id = None
                fuel_price = None

                rate_plan_id = None
                rate_plan_detail_id = None

                precio_unitario = None
                precio_total = None
                bonificacion_piloto = None

                pricing_version = 1

        # ============================================================
        # 9. ARCHIVO TEMPORAL
        # ============================================================

        os.makedirs(
            temp_dir,
            exist_ok=True,
        )

        file_ext = (
            os.path.splitext(
                file.filename or ""
            )[1]
            or ".jpg"
        )

        temp_filename = (
            f"{uuid.uuid4()}{file_ext}"
        )

        temp_file_path = os.path.join(
            temp_dir,
            temp_filename,
        )

        with open(
            temp_file_path,
            "wb",
        ) as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # ============================================================
        # 10. CLOUDINARY
        # ============================================================

        try:
            upload_result = (
                cloudinary.uploader.upload(
                    temp_file_path,
                    folder="ordenes_boletas",
                    resource_type="image",
                )
            )

        except Exception as upload_error:
            raise HTTPException(
                status_code=500,
                detail=(
                    "No fue posible subir la imagen "
                    f"de la boleta: {upload_error}"
                ),
            ) from upload_error

        image_url = upload_result.get(
            "secure_url"
        )

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Cloudinary no devolvió "
                    "la URL de la imagen."
                ),
            )

        # ============================================================
        # 11. CREAR DOCUMENTO
        # ============================================================

        new_document = Document(
            fecha=fecha_normalizada,

            origen=origen_final,
            destino=destino_final,

            producto=producto.upper(),
            piloto=final_piloto,

            no_orden_carga=(
                no_orden_carga.upper()
            ),

            peso_entregado=(
                peso_entregado.upper()
            ),

            no_constancia_viaje=(
                no_constancia_viaje.upper()
            ),

            combustible_consumido=(
                combustible_consumido
            ),

            no_vale=no_vale.upper(),

            cliente_id=cliente_id,
            truck_id=truck_id,

            # Puede ser NULL si la ruta todavía
            # no está configurada.
            route_id=route_id,

            # --------------------------------------------------------
            # Snapshot combustible
            # --------------------------------------------------------

            fuel_price_id=fuel_price_id,
            fuel_price=fuel_price,

            # --------------------------------------------------------
            # Snapshot tarifa
            # --------------------------------------------------------

            rate_plan_id=rate_plan_id,
            rate_plan_detail_id=(
                rate_plan_detail_id
            ),

            precio_unitario=precio_unitario,
            precio_total=precio_total,

            bonificacion_piloto=(
                bonificacion_piloto
            ),

            pricing_version=pricing_version,

            image_path=image_url,
            raw_text="",

            created_by_user_id=(
                current_user.id
            ),

            created_by_username=(
                current_user.username
            ),
        )

        # ============================================================
        # 12. GUARDAR
        # ============================================================

        try:
            db.add(new_document)
            db.commit()
            db.refresh(new_document)

        except Exception as database_error:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "No fue posible guardar la boleta "
                    "en la base de datos: "
                    f"{database_error}"
                ),
            ) from database_error

        # ============================================================
        # 13. LOG FINAL
        # ============================================================

        if route_id is None:
            estado_pricing = (
                "PENDIENTE_RUTA"
            )

        elif precio_total is None:
            estado_pricing = (
                "PENDIENTE_TARIFA"
            )

        else:
            estado_pricing = "TARIFADO"

        print(
            "DOCUMENTO CREADO:",
            {
                "id": new_document.id,
                "fecha": new_document.fecha,
                "origen": new_document.origen,
                "destino": new_document.destino,
                "route_id": new_document.route_id,
                "precio_total": (
                    new_document.precio_total
                ),
                "estado_pricing": estado_pricing,
            },
        )

        return new_document

    finally:
        # ============================================================
        # 14. LIMPIEZA
        # ============================================================

        if (
            temp_file_path
            and os.path.exists(
                temp_file_path
            )
        ):
            try:
                os.remove(
                    temp_file_path
                )
            except OSError:
                pass
              
@app.post("/auth/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == payload.username.upper()
    ).first()

    if not user or user.activo != "SI":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "piloto_nombre": user.piloto_nombre
    }


@app.post("/users", response_model=UserResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    username = payload.username.upper().strip()
    role = payload.role.upper().strip()

    existing = db.query(User).filter(User.username == username).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    if role not in {"ADMIN", "ENCARGADO", "PILOTO"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    if len(payload.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="Password must contain at least 6 characters")

    piloto_nombre = payload.piloto_nombre.upper().strip() if payload.piloto_nombre else None
    if role == "PILOTO":
        if not piloto_nombre:
            raise HTTPException(status_code=400, detail="Pilot users must have piloto_nombre")
        pilot = db.query(Pilot).filter(
            func.upper(func.trim(Pilot.nombre)) == piloto_nombre,
            Pilot.activo == "SI"
        ).first()
        if not pilot:
            raise HTTPException(status_code=400, detail="Active pilot not found")
        piloto_nombre = pilot.nombre
    else:
        piloto_nombre = None

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        role=role,
        piloto_nombre=piloto_nombre,
        activo="SI"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@app.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    return db.query(User).order_by(User.username.asc()).all()

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "username" in data:
        username = (data["username"] or "").upper().strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        if db.query(User).filter(User.username == username, User.id != user_id).first():
            raise HTTPException(status_code=400, detail="User already exists")
        user.username = username
    if "role" in data:
        role = (data["role"] or "").upper().strip()
        if role not in {"ADMIN", "ENCARGADO", "PILOTO"}:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
    if "piloto_nombre" in data:
        user.piloto_nombre = (data["piloto_nombre"] or "").upper().strip() or None
    if user.role == "PILOTO":
        if not user.piloto_nombre:
            raise HTTPException(status_code=400, detail="Pilot users must have piloto_nombre")
        pilot = db.query(Pilot).filter(func.upper(func.trim(Pilot.nombre)) == user.piloto_nombre, Pilot.activo == "SI").first()
        if not pilot:
            raise HTTPException(status_code=400, detail="Active pilot not found")
        user.piloto_nombre = pilot.nombre
    else:
        user.piloto_nombre = None
    if "activo" in data:
        activo = (data["activo"] or "").upper().strip()
        if activo not in {"SI", "NO"}:
            raise HTTPException(status_code=400, detail="activo must be SI or NO")
        if user.id == current_user.id and activo == "NO":
            raise HTTPException(status_code=400, detail="You cannot deactivate your own user")
        user.activo = activo
    try:
        db.commit(); db.refresh(user)
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail=f"Error updating user: {exc}")
    return user

@app.put("/users/{user_id}/password")
def update_user_password(user_id: int, payload: UserPasswordUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    password = payload.password.strip()
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must contain at least 6 characters")
    user.password_hash = hash_password(password)
    try:
        db.commit()
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail=f"Error updating password: {exc}")
    return {"message": "Password updated successfully"}

@app.delete("/users/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own user")
    user.activo = "NO"
    try:
        db.commit()
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail=f"Error deactivating user: {exc}")
    return {"message": "User deactivated successfully"}

@app.post("/routes", response_model=RouteResponse)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    route = Route(
        nombre=payload.nombre.upper().strip(),
        origen=payload.origen.upper().strip(),
        destino=payload.destino.upper().strip(),
        distancia_km=payload.distancia_km,
        costo_viaje=payload.costo_viaje,
        bonificacion_piloto=payload.bonificacion_piloto,
        tiempo_estimado=payload.tiempo_estimado.upper().strip()
        if payload.tiempo_estimado else None,
        cliente=payload.cliente.upper().strip()
        if payload.cliente else None,
        activo="SI"
    )

    db.add(route)
    db.commit()
    db.refresh(route)

    return route


@app.get("/routes", response_model=list[RouteResponse])
def get_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return (
        db.query(Route)
        .filter(Route.activo == "SI")
        .order_by(Route.nombre.asc())
        .all()
    )


@app.put("/routes/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int,
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    route = db.query(Route).filter(Route.id == route_id).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.nombre = payload.nombre.upper().strip()
    route.origen = payload.origen.upper().strip()
    route.destino = payload.destino.upper().strip()
    route.distancia_km = payload.distancia_km
    route.costo_viaje = payload.costo_viaje
    route.bonificacion_piloto = payload.bonificacion_piloto
    route.tiempo_estimado = (
        payload.tiempo_estimado.upper().strip()
        if payload.tiempo_estimado else None
    )
    route.cliente = (
        payload.cliente.upper().strip()
        if payload.cliente else None
    )

    db.commit()
    db.refresh(route)

    return route


@app.delete("/routes/{route_id}")
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    route = db.query(Route).filter(Route.id == route_id).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.activo = "NO"
    db.commit()

    return {"message": "Route disabled successfully"}

@app.post("/clients", response_model=ClientResponse)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    client = Client(
        nombre=payload.nombre.upper().strip(),
        nit=payload.nit.upper().strip() if payload.nit else None,
        telefono=payload.telefono,
        email=payload.email,
        direccion=payload.direccion.upper().strip() if payload.direccion else None,
        contacto=payload.contacto.upper().strip() if payload.contacto else None,
        activo="SI"
    )

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


@app.get("/clients", response_model=list[ClientResponse])
def get_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return (
        db.query(Client)
        .filter(Client.activo == "SI")
        .order_by(Client.nombre.asc())
        .all()
    )


@app.put("/clients/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.nombre = payload.nombre.upper().strip()
    client.nit = payload.nit.upper().strip() if payload.nit else None
    client.telefono = payload.telefono
    client.email = payload.email
    client.direccion = payload.direccion.upper().strip() if payload.direccion else None
    client.contacto = payload.contacto.upper().strip() if payload.contacto else None

    db.commit()
    db.refresh(client)

    return client


@app.delete("/clients/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.activo = "NO"
    db.commit()

    return {"message": "Client disabled successfully"}

@app.post("/trucks", response_model=TruckResponse)
def create_truck(
    payload: TruckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    truck = Truck(
        codigo=payload.codigo.upper().strip() if payload.codigo else None,
        placa=payload.placa.upper().strip() if payload.placa else None,
        marca=payload.marca.upper().strip() if payload.marca else None,
        modelo=payload.modelo.upper().strip() if payload.modelo else None,
        anio=payload.anio,
        vin=payload.vin.upper().strip() if payload.vin else None,
        motor=payload.motor.upper().strip() if payload.motor else None,
        color=payload.color.upper().strip() if payload.color else None,
        capacidad=payload.capacidad,
        kilometraje_actual=payload.kilometraje_actual,
        consumo_esperado=payload.consumo_esperado,
        piloto_asignado=payload.piloto_asignado.upper().strip()
        if payload.piloto_asignado else None,
        estado=payload.estado.upper().strip() if payload.estado else "ACTIVO",
        fecha_compra=payload.fecha_compra,
        valor_compra=payload.valor_compra,
        valor_residual=payload.valor_residual,
        vida_util_anios=payload.vida_util_anios,
        metodo_depreciacion=payload.metodo_depreciacion.upper().strip()
        if payload.metodo_depreciacion else "LINEA RECTA",
        proveedor=payload.proveedor.upper().strip() if payload.proveedor else None,
        seguro=payload.seguro,
        observaciones=payload.observaciones
    )

    db.add(truck)
    db.commit()
    db.refresh(truck)

    return truck


@app.get("/trucks", response_model=list[TruckResponse])
def get_trucks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return (
        db.query(Truck)
        .filter(Truck.estado != "INACTIVO")
        .order_by(Truck.codigo.asc())
        .all()
    )


@app.put("/trucks/{truck_id}", response_model=TruckResponse)
def update_truck(
    truck_id: int,
    payload: TruckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    truck = db.query(Truck).filter(Truck.id == truck_id).first()

    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    data = payload.dict(exclude_unset=True)

    for key, value in data.items():
        if isinstance(value, str):
            setattr(truck, key, value.upper().strip())
        else:
            setattr(truck, key, value)

    db.commit()
    db.refresh(truck)

    return truck


@app.delete("/trucks/{truck_id}")
def delete_truck(
    truck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    truck = db.query(Truck).filter(Truck.id == truck_id).first()

    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    truck.estado = "INACTIVO"
    db.commit()

    return {"message": "Truck disabled successfully"}

@app.get("/financial/settings", response_model=FinancialSettingsResponse)
def get_financial_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    settings = db.query(FinancialSettings).first()

    if not settings:
        settings = FinancialSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings

# ==========================================
# PRECIOS DE COMBUSTIBLE
# ==========================================

@app.get("/fuel-prices", response_model=list[FuelPriceResponse])
def get_fuel_prices(db: Session = Depends(get_db)):
    return (
        db.query(FuelPrice)
        .order_by(FuelPrice.fecha.desc())
        .all()
    )


@app.get("/fuel-prices/latest", response_model=FuelPriceResponse)
def get_latest_fuel_price(db: Session = Depends(get_db)):
    price = (
        db.query(FuelPrice)
        .order_by(FuelPrice.fecha.desc())
        .first()
    )

    if not price:
        raise HTTPException(
            status_code=404,
            detail="No existe precio de combustible."
        )

    return price


@app.post("/fuel-prices", response_model=FuelPriceResponse)
def create_fuel_price(
    fuel: FuelPriceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO")),
):
    existing = (
        db.query(FuelPrice)
        .filter(FuelPrice.fecha == fuel.fecha)
        .first()
    )

    if existing:

        existing.precio_galon = fuel.precio_galon
        existing.fuente = fuel.fuente
        existing.observaciones = fuel.observaciones

        db.commit()
        db.refresh(existing)

        return existing

    new_price = FuelPrice(**fuel.model_dump())

    db.add(new_price)
    db.commit()
    db.refresh(new_price)

    return new_price

@app.put("/financial/settings", response_model=FinancialSettingsResponse)
def update_financial_settings(
    payload: FinancialSettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    settings = db.query(FinancialSettings).first()

    if not settings:
        settings = FinancialSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    data = payload.dict(exclude_unset=True)

    for key, value in data.items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return settings

# ==========================================
# VEHICLE TYPES
# ==========================================

@app.post("/vehicle-types", response_model=VehicleTypeResponse)
def create_vehicle_type(
    payload: VehicleTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    item = VehicleType(
        nombre=payload.nombre.upper().strip(),
        descripcion=payload.descripcion,
        ejes=payload.ejes,
        capacidad=payload.capacidad,
        activo="SI"
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@app.get("/vehicle-types", response_model=list[VehicleTypeResponse])
def get_vehicle_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(VehicleType)
        .filter(VehicleType.activo == "SI")
        .order_by(VehicleType.nombre.asc())
        .all()
    )


@app.delete("/vehicle-types/{item_id}")
def delete_vehicle_type(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    item = db.query(VehicleType).filter(VehicleType.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Vehicle type not found")

    item.activo = "NO"
    db.commit()

    return {"message": "Vehicle type disabled successfully"}


# ==========================================
# CHARGE TYPES
# ==========================================

@app.post("/charge-types", response_model=ChargeTypeResponse)
def create_charge_type(
    payload: ChargeTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    item = ChargeType(
        nombre=payload.nombre.upper().strip(),
        descripcion=payload.descripcion,
        activo="SI"
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@app.get("/charge-types", response_model=list[ChargeTypeResponse])
def get_charge_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(ChargeType)
        .filter(ChargeType.activo == "SI")
        .order_by(ChargeType.nombre.asc())
        .all()
    )


@app.delete("/charge-types/{item_id}")
def delete_charge_type(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    item = db.query(ChargeType).filter(ChargeType.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Charge type not found")

    item.activo = "NO"
    db.commit()

    return {"message": "Charge type disabled successfully"}

@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role": user.role,
        "piloto_nombre": user.piloto_nombre
    }
