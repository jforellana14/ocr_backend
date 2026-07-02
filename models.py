from sqlalchemy import Column, Integer, String, Text, DateTime, Float
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
    created_by_user_id = Column(Integer, nullable=True)
    created_by_username = Column(String, nullable=True)
    combustible = Column(Float, nullable=True)
    costo_viaje = Column(Float, nullable=True)
    bonificacion_piloto = Column(Float, nullable=True)
    distancia_viaje = Column(Float, nullable=True)
    no_vale = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    distancia_km = Column(Float, nullable=True)
    costo_viaje = Column(Float, nullable=True)
    bonificacion_piloto = Column(Float, nullable=True)
    tiempo_estimado = Column(String, nullable=True)
    cliente = Column(String, nullable=True)
    activo = Column(String, default="SI")
    created_at = Column(DateTime, default=datetime.utcnow)

class Pilot(Base):
    __tablename__ = "pilots"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    activo = Column(String, default="SI")
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # ADMIN, ENCARGADO, PILOTO
    piloto_nombre = Column(String, nullable=True)
    activo = Column(String, default="SI")
    created_at = Column(DateTime, default=datetime.utcnow)