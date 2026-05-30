from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from fastapi import Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
import uuid

from database import SessionLocal, engine
from models import Base, Document
from schemas import DocumentCreate, DocumentResponse, DocumentUpdate
from fastapi import HTTPException

from fastapi import UploadFile, File
import shutil

from openpyxl import Workbook
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OCR Document System")

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
    
@app.post("/documents", response_model=DocumentResponse)
def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db)
):
    db_document = Document(
        document_type=document.document_type,
        extracted_name=document.extracted_name,
        extracted_id=document.extracted_id,
        extracted_date=document.extracted_date,
        raw_text=document.raw_text
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document

from sqlalchemy import text

@app.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db)
):
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
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}


@app.get("/pilots")
def get_pilots(db: Session = Depends(get_db)):
    pilots = (
        db.query(Document.piloto)
        .filter(Document.piloto.isnot(None))
        .distinct()
        .all()
    )

    return [
        pilot[0]
        for pilot in pilots
        if pilot[0] and pilot[0].strip()
    ]

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
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
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

    new_document = Document(
        fecha=fecha.upper(),
        origen=origen.upper(),
        destino=destino.upper(),
        producto=producto.upper(),
        piloto=piloto.upper(),
        no_orden_carga=no_orden_carga.upper(),
        peso_entregado=peso_entregado.upper(),
        no_constancia_viaje=no_constancia_viaje.upper(),
        image_path=image_url,
        raw_text=""
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return new_document

@app.get("/documents", response_model=list[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):
    return db.query(Document).all()