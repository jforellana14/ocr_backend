from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from fastapi import Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
import uuid
from models import Base, Document, Pilot, User, Route, Client, Truck, FinancialSettings, FuelPrice, VehicleType, ChargeType
from schemas import UserCreate, UserResponse, LoginRequest, RouteCreate, RouteResponse, ClientCreate, ClientResponse, TruckCreate, TruckResponse, FinancialSettingsCreate, FinancialSettingsResponse, FuelPriceCreate, FuelPriceResponse, VehicleTypeCreate, VehicleTypeResponse, ChargeTypeCreate, ChargeTypeResponse
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import SessionLocal, engine
from schemas import DocumentCreate, DocumentResponse, DocumentUpdate, PilotCreate, PilotResponse
from fastapi import HTTPException

from fastapi import UploadFile, File
import shutil
from fastapi.responses import FileResponse
from openpyxl import Workbook
from routers import vehicle_types
import os

Base.metadata.create_all(bind=engine)

from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS combustible DOUBLE PRECISION;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS no_vale VARCHAR;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS costo_viaje DOUBLE PRECISION;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS bonificacion_piloto DOUBLE PRECISION;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS distancia_viaje DOUBLE PRECISION;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS cliente_id INTEGER;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS truck_id INTEGER;
    """))

    conn.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS route_id INTEGER;
    """))

    conn.commit()

app = FastAPI(title="OCR Document System")

app.include_router(vehicle_types.router)

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET")
ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)
security = HTTPBearer()


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str):
    return pwd_context.verify(password, password_hash)


def create_token(user: User):
    payload = {
        "sub": user.username,
        "role": user.role,
        "piloto_nombre": user.piloto_nombre
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        user = db.query(User).filter(User.username == username).first()

        if not user or user.activo != "SI":
            raise HTTPException(status_code=401, detail="Invalid user")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_roles(*roles):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)
os.makedirs("uploads", exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "OCR Backend Running"}
    
from typing import Optional
from fastapi import Query

@app.get("/pilots/filter")
def get_pilots_filter(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Document.piloto)
        .distinct()
        .all()
    )

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

from sqlalchemy import text

@app.post("/pilots", response_model=PilotResponse)
def create_pilot(
    pilot: PilotCreate,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    existing = db.query(Pilot).filter(Pilot.id == pilot_id).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Pilot not found")

    existing.nombre = pilot.nombre.upper().strip()

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
    db: Session = Depends(get_db)
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
        raise HTTPException(status_code=403, detail="Pilots cannot edit documents")
    
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    data = payload.dict(exclude_unset=True)

    for key, value in data.items():
        if isinstance(value, str):
            setattr(document, key, value.upper())
        else:
            setattr(document, key, value)

    db.commit()
    db.refresh(document)

    return document


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "PILOTO":
        raise HTTPException(status_code=403, detail="Pilots cannot delete documents")
    
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}


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
    combustible: float = Form(0),
    no_vale: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_file_path = os.path.join(temp_dir, temp_filename)

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    upload_result = cloudinary.uploader.upload(
        temp_file_path,
        folder="ordenes_boletas",
        resource_type="image"
    )

    image_url = upload_result.get("secure_url")

    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)

    final_piloto = piloto.upper().strip()

    if current_user.role == "PILOTO":
        final_piloto = current_user.piloto_nombre.upper().strip()

    new_document = Document(
        fecha=fecha.upper(),
        origen=origen.upper(),
        destino=destino.upper(),
        producto=producto.upper(),
        piloto=final_piloto,
        no_orden_carga=no_orden_carga.upper(),
        peso_entregado=peso_entregado.upper(),
        no_constancia_viaje=no_constancia_viaje.upper(),
        combustible=combustible,
        no_vale=no_vale.upper(),    
        image_path=image_url,
        raw_text="",
        created_by_user_id=current_user.id,
        created_by_username=current_user.username
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return new_document

@app.get("/export/excel")
def export_excel(
    piloto: str | None = None,
    origen: str | None = None,
    destino: str | None = None,
    producto: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document)

    if current_user.role == "PILOTO":
        query = query.filter(Document.created_by_user_id == current_user.id)

    if piloto:
        query = query.filter(Document.piloto.ilike(f"%{piloto}%"))

    if origen:
        query = query.filter(Document.origen.ilike(f"%{origen}%"))

    if destino:
        query = query.filter(Document.destino.ilike(f"%{destino}%"))

    if producto:
        query = query.filter(Document.producto.ilike(f"%{producto}%"))

    documents = query.order_by(Document.created_at.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Ordenes"

    headers = [
        "ID",
        "Fecha",
        "Origen",
        "Destino",
        "Producto",
        "Piloto",
        "Usuario",
        "User ID",
        "No. Orden de Carga",
        "Peso Entregado",
        "Combustible (galones)",
        "No. Vale",
        "No. Constancia de Viaje",
        "Imagen",
        "Created At"
    ]

    ws.append(headers)

    for doc in documents:
        ws.append([
            doc.id,
            doc.fecha,
            doc.origen,
            doc.destino,
            doc.producto,
            doc.piloto,
            doc.created_by_username,
            doc.created_by_user_id,
            doc.no_orden_carga,
            doc.peso_entregado,
            doc.combustible,
            doc.no_vale,
            doc.no_constancia_viaje,
            doc.image_path,
            str(doc.created_at)
        ])

    os.makedirs("exports", exist_ok=True)

    file_path = "exports/ordenes_filtradas.xlsx"
    wb.save(file_path)

    return FileResponse(
        path=file_path,
        filename="ordenes_filtradas.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/auth/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == payload.username.upper()
    ).first()

    if not user:
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

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        role=role,
        piloto_nombre=payload.piloto_nombre.upper().strip()
        if payload.piloto_nombre else None,
        activo="SI"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

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
    db: Session = Depends(get_db)
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