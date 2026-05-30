from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    fecha = Column(String, nullable=True)
    origen = Column(String, nullable=True)
    destino = Column(String, nullable=True)
    producto = Column(String, nullable=True)
    no_orden_carga = Column(String, nullable=True)
    peso_entregado = Column(String, nullable=True)
    no_constancia_viaje = Column(String, nullable=True)
    piloto = Column(String, nullable=True)
    image_path = Column(String, nullable=True)

    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pilot(Base):
    __tablename__ = "pilots"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    activo = Column(String, default="SI")
    created_at = Column(DateTime, default=datetime.utcnow)