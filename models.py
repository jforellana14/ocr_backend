from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Date
from datetime import datetime
from database import Base
from sqlalchemy.orm import relationship

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
    cliente_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    truck_id = Column(Integer, ForeignKey("trucks.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    no_vale = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    cliente = relationship("Client")
    camion = relationship("Truck")
    ruta = relationship("Route")
    

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

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)

    nombre = Column(String, nullable=False)
    nit = Column(String)
    telefono = Column(String)
    email = Column(String)
    direccion = Column(String)

    contacto = Column(String)

    activo = Column(String, default="SI")

    created_at = Column(DateTime, default=datetime.utcnow)


class Truck(Base):
    __tablename__ = "trucks"

    id = Column(Integer, primary_key=True, index=True)

    codigo = Column(String, unique=True, index=True)
    placa = Column(String, unique=True, index=True)

    marca = Column(String)
    modelo = Column(String)
    anio = Column(Integer)
    vin = Column(String)
    motor = Column(String)
    color = Column(String)

    capacidad = Column(Float)
    kilometraje_actual = Column(Float, default=0)
    consumo_esperado = Column(Float)

    piloto_asignado = Column(String)
    estado = Column(String, default="ACTIVO")

    fecha_compra = Column(Date)
    valor_compra = Column(Float)
    valor_residual = Column(Float)
    vida_util_anios = Column(Integer)
    metodo_depreciacion = Column(String, default="LINEA RECTA")

    proveedor = Column(String)
    seguro = Column(Float)
    observaciones = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class FinancialSettings(Base):
    __tablename__ = "financial_settings"

    id = Column(Integer, primary_key=True)

    porcentaje_isr = Column(Float, default=25)

    porcentaje_prestaciones = Column(Float, default=30)

    porcentaje_mantenimiento = Column(Float, default=8)

    costo_combustible_galon = Column(Float, default=35)

    hosting = Column(Float, default=0)

    telefono = Column(Float, default=0)

    internet = Column(Float, default=0)

    seguros = Column(Float, default=0)

    otros = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)