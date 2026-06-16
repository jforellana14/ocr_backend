from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from fastapi import Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
import uuid
from models import Base, Document, Pilot, User
from schemas import UserCreate, UserResponse, LoginRequest
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import SessionLocal, engine
from models import Base, Document, Pilot
from schemas import DocumentCreate, DocumentResponse, DocumentUpdate, PilotCreate, PilotResponse
from fastapi import HTTPException

from fastapi import UploadFile, File
import shutil
from fastapi.responses import FileResponse
from openpyxl import Workbook
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

    conn.commit()

app = FastAPI(title="OCR Document System")

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


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role": user.role,
        "piloto_nombre": user.piloto_nombre
    }