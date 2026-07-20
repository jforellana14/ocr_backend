from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Date
from datetime import datetime
from database import Base
from sqlalchemy.orm import relationship

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # ==========================
    # Información de la boleta
    # ==========================
    fecha = Column(String, nullable=True)
    origen = Column(String, nullable=True)
    destino = Column(String, nullable=True)
    producto = Column(String, nullable=True)

    no_orden_carga = Column(String, nullable=True)
    no_constancia_viaje = Column(String, nullable=True)

    peso_entregado = Column(String, nullable=True)

    image_path = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)

    # ==========================
    # Relaciones
    # ==========================
    cliente_id = Column(
        Integer,
        ForeignKey("clients.id"),
        nullable=True
    )

    truck_id = Column(
        Integer,
        ForeignKey("trucks.id"),
        nullable=True
    )

    route_id = Column(
        Integer,
        ForeignKey("routes.id"),
        nullable=True
    )

    piloto = Column(String, nullable=True)

    # ==========================
    # Operación
    # ==========================
    distancia_viaje = Column(Float, nullable=True)

    combustible_consumido = Column(Float, nullable=True)

    no_vale = Column(String, nullable=True)

    # ==========================
    # Pricing Engine Snapshot
    # ==========================
    fuel_price_id = Column(
        Integer,
        ForeignKey("fuel_prices.id"),
        nullable=True
    )

    fuel_price = Column(Float, nullable=True)

    rate_plan_id = Column(
        Integer,
        ForeignKey("rate_plans.id"),
        nullable=True
    )

    rate_plan_detail_id = Column(
        Integer,
        ForeignKey("rate_plan_details.id"),
        nullable=True
    )

    precio_unitario = Column(Float, nullable=True)

    precio_total = Column(Float, nullable=True)

    bonificacion_piloto = Column(Float, nullable=True)

    pricing_version = Column(Integer, default=1)

    # ==========================
    # Auditoría
    # ==========================
    created_by_user_id = Column(Integer, nullable=True)

    created_by_username = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ==========================
    # Relaciones ORM
    # ==========================
    cliente = relationship("Client")

    camion = relationship("Truck")

    ruta = relationship("Route")

    fuel_price_ref = relationship("FuelPrice")

    rate_plan = relationship("RatePlan")

    rate_plan_detail = relationship("RatePlanDetail")    

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
    vehicle_type_id = Column(Integer, ForeignKey("vehicle_types.id"), nullable=True)
    vehicle_type = relationship("VehicleType")
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

class FuelPrice(Base):
    __tablename__ = "fuel_prices"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, unique=True)
    precio_galon = Column(Float, nullable=False)
    fuente = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TariffHeader(Base):
    __tablename__ = "tariff_headers"

    id = Column(Integer, primary_key=True, index=True)

    nombre = Column(String, nullable=False)

    cliente_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)

    vehicle_type_id = Column(
        Integer,
        ForeignKey("vehicle_types.id"),
        nullable=False
    )

    charge_type_id = Column(
        Integer,
        ForeignKey("charge_types.id"),
        nullable=False
    )

    vehicle_type = relationship("VehicleType")

    charge_type = relationship("ChargeType")

    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)

    activo = Column(String, default="SI")

    created_at = Column(DateTime, default=datetime.utcnow)

    cliente = relationship("Client")
    ruta = relationship("Route")


class TariffDetail(Base):
    __tablename__ = "tariff_details"

    id = Column(Integer, primary_key=True, index=True)

    tariff_header_id = Column(Integer, ForeignKey("tariff_headers.id"), nullable=False)

    combustible_min = Column(Float, nullable=True)
    combustible_max = Column(Float, nullable=True)

    peso_min = Column(Float, nullable=True)
    peso_max = Column(Float, nullable=True)

    precio_por_unidad_peso = Column(Float, nullable=False)

    bonificacion_piloto = Column(Float, nullable=True)
    margen_estimado = Column(Float, nullable=True)

    activo = Column(String, default="SI")

    created_at = Column(DateTime, default=datetime.utcnow)

    tariff_header = relationship("TariffHeader")

class VehicleType(Base):
    __tablename__ = "vehicle_types"

    id = Column(Integer, primary_key=True, index=True)

    nombre = Column(String, nullable=False, unique=True)

    descripcion = Column(Text, nullable=True)

    ejes = Column(Integer, nullable=True)

    capacidad = Column(Float, nullable=True)

    activo = Column(String, default="SI")

    created_at = Column(DateTime, default=datetime.utcnow)


class ChargeType(Base):
    __tablename__ = "charge_types"

    id = Column(Integer, primary_key=True, index=True)

    nombre = Column(String, nullable=False, unique=True)

    descripcion = Column(Text, nullable=True)

    activo = Column(String, default="SI")

    created_at = Column(DateTime, default=datetime.utcnow)

class RatePlan(Base):
    __tablename__ = "rate_plans"

    id = Column(Integer, primary_key=True, index=True)

    codigo = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)

    scope = Column(String, default="CLIENT")  # GLOBAL / CLIENT

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    vehicle_type_id = Column(Integer, ForeignKey("vehicle_types.id"), nullable=False)
    charge_type_id = Column(Integer, ForeignKey("charge_types.id"), nullable=False)

    producto = Column(String, nullable=True)

    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)

    moneda = Column(String, default="GTQ")
    version = Column(Integer, default=1)

    estado = Column(String, default="ACTIVO")  # ACTIVO / PENDIENTE / EXPIRADO
    observaciones = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client")
    route = relationship("Route")
    vehicle_type = relationship("VehicleType")
    charge_type = relationship("ChargeType")


class RatePlanDetail(Base):
    __tablename__ = "rate_plan_details"

    id = Column(Integer, primary_key=True, index=True)

    rate_plan_id = Column(Integer, ForeignKey("rate_plans.id"), nullable=False)

    combustible_min = Column(Float, nullable=True)
    combustible_max = Column(Float, nullable=True)

    peso_min = Column(Float, nullable=True)
    peso_max = Column(Float, nullable=True)

    precio_unitario = Column(Float, nullable=False)

    bonificacion_piloto = Column(Float, nullable=True)
    margen_estimado = Column(Float, nullable=True)

    activo = Column(String, default="SI")

    created_at = Column(DateTime, default=datetime.utcnow)

    rate_plan = relationship("RatePlan")