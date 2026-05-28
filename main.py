from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from fastapi import Form
import uuid

from database import SessionLocal, engine
from models import Base, Document
from schemas import DocumentCreate, DocumentResponse

from fastapi import UploadFile, File
import shutil

from ocr_utils import process_document

from openpyxl import Workbook
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OCR Document System")


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

@app.post("/documents/manual", response_model=DocumentResponse)
async def create_manual_document(
    fecha: str = Form(""),
    origen: str = Form(""),
    destino: str = Form(""),
    producto: str = Form(""),
    no_orden_carga: str = Form(""),
    peso_entregado: str = Form(""),
    no_constancia_viaje: str = Form(""),
    piloto: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    os.makedirs("uploads", exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join("uploads", filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_document = Document(
        fecha=fecha.upper(),
        origen=origen.upper(),
        destino=destino.upper(),
        producto=producto.upper(),
        piloto=piloto.upper(),
        no_orden_carga=no_orden_carga.upper(),
        peso_entregado=peso_entregado.upper(),
        no_constancia_viaje=no_constancia_viaje.upper(),
        image_path=file_path,
        raw_text=""
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document

@app.get("/documents", response_model=list[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):
    return db.query(Document).all()

@app.post("/scan")
async def scan_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

        file_path = f"temp_{file.filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_data = process_document(file_path)

        db_document = Document(
            fecha=extracted_data["fecha"],
            origen=extracted_data["origen"],
            destino=extracted_data["destino"],
            producto=extracted_data["producto"],
            no_orden_carga=extracted_data["no_orden_carga"],
            peso_entregado=extracted_data["peso_entregado"],
            no_constancia_viaje=extracted_data["no_constancia_viaje"],

            raw_text=extracted_data["raw_text"]
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        return db_document

@app.post("/scan-preview")
async def scan_preview(
    file: UploadFile = File(...)
):
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_data = process_document(file_path)

    return extracted_data

@app.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):

    documents = db.query(Document).all()

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
        "No. Orden de Carga",
        "Peso Entregado",
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
            doc.no_orden_carga,
            doc.peso_entregado,
            doc.no_constancia_viaje,
            doc.image_path,
            str(doc.created_at)
        ])

    os.makedirs("exports", exist_ok=True)

    file_path = "exports/documents.xlsx"
    wb.save(file_path)

    return FileResponse(
        path=file_path,
        filename="documents.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )