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
    combustible: float | None = None
    no_vale: str | None = None

class DocumentUpdate(BaseModel):
    fecha: Optional[str] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    producto: Optional[str] = None
    piloto: Optional[str] = None
    no_orden_carga: Optional[str] = None
    peso_entregado: Optional[str] = None
    no_constancia_viaje: Optional[str] = None
    combustible: Optional[float] = None
    costo_viaje: Optional[float] = None
    bonificacion_piloto: Optional[float] = None
    distancia_viaje: Optional[float] = None
    no_vale: Optional[str] = None
    cliente_id: Optional[int] = None
    truck_id: Optional[int] = None
    route_id: Optional[int] = None

class PilotCreate(BaseModel):
    nombre: str


class PilotResponse(BaseModel):
    id: int
    nombre: str
    activo: str
    created_at: datetime

    class Config:
        from_attributes = True    

class DocumentResponse(BaseModel):
    id: int
    fecha: str
    origen: str
    destino: str
    producto: str
    piloto: str
    no_orden_carga: str
    peso_entregado: str
    no_constancia_viaje: str
    combustible: Optional[float] = None
    costo_viaje: Optional[float] = None
    bonificacion_piloto: Optional[float] = None
    distancia_viaje: Optional[float] = None
    no_vale: Optional[str] = None
    image_path: Optional[str] = None
    raw_text: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by_username: Optional[str] = None
    created_at: datetime
    cliente_id: Optional[int] = None
    truck_id: Optional[int] = None
    route_id: Optional[int] = None

    class Config:
        from_attributes = True

class RouteCreate(BaseModel):
    nombre: str
    origen: str
    destino: str
    distancia_km: Optional[float] = None
    costo_viaje: Optional[float] = None
    bonificacion_piloto: Optional[float] = None
    tiempo_estimado: Optional[str] = None
    cliente: Optional[str] = None


class RouteResponse(BaseModel):
    id: int
    nombre: str
    origen: str
    destino: str
    distancia_km: Optional[float] = None
    costo_viaje: Optional[float] = None
    bonificacion_piloto: Optional[float] = None
    tiempo_estimado: Optional[str] = None
    cliente: Optional[str] = None
    activo: str

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    piloto_nombre: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    piloto_nombre: Optional[str] = None
    activo: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str

class ClientCreate(BaseModel):
    nombre: str
    nit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    contacto: Optional[str] = None


class ClientResponse(BaseModel):
    id: int
    nombre: str
    nit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    contacto: Optional[str] = None
    activo: str

    class Config:
        from_attributes = True


class TruckCreate(BaseModel):
    codigo: Optional[str] = None
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    vin: Optional[str] = None
    motor: Optional[str] = None
    color: Optional[str] = None
    capacidad: Optional[float] = None
    kilometraje_actual: Optional[float] = 0
    consumo_esperado: Optional[float] = None
    piloto_asignado: Optional[str] = None
    estado: Optional[str] = "ACTIVO"
    fecha_compra: Optional[date] = None
    valor_compra: Optional[float] = None
    valor_residual: Optional[float] = None
    vida_util_anios: Optional[int] = None
    metodo_depreciacion: Optional[str] = "LINEA RECTA"
    proveedor: Optional[str] = None
    seguro: Optional[float] = None
    observaciones: Optional[str] = None


class TruckResponse(TruckCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FinancialSettingsCreate(BaseModel):
    porcentaje_isr: Optional[float] = 25
    porcentaje_prestaciones: Optional[float] = 30
    porcentaje_mantenimiento: Optional[float] = 8
    costo_combustible_galon: Optional[float] = 35
    hosting: Optional[float] = 0
    telefono: Optional[float] = 0
    internet: Optional[float] = 0
    seguros: Optional[float] = 0
    otros: Optional[float] = 0


class FinancialSettingsResponse(FinancialSettingsCreate):
    id: int

    class Config:
        from_attributes = True