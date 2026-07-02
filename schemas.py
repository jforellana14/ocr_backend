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