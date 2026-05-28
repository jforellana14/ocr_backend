from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    fecha: Optional[str] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    producto: Optional[str] = None
    no_orden_carga: Optional[str] = None
    peso_entregado: Optional[str] = None
    no_constancia_viaje: Optional[str] = None
    raw_text: Optional[str] = None
    piloto: Optional[str] = None
    image_path: Optional[str] = None


class DocumentResponse(DocumentCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True