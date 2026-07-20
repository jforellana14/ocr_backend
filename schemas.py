from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


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
    combustible_consumido: Optional[float] = None
    distancia_viaje: Optional[float] = None
    no_vale: Optional[str] = None
    cliente_id: Optional[int] = None
    truck_id: Optional[int] = None
    route_id: Optional[int] = None


class DocumentUpdate(DocumentCreate):
    pass


class DocumentResponse(DocumentCreate):
    id: int

    fuel_price_id: Optional[int] = None
    fuel_price: Optional[float] = None
    rate_plan_id: Optional[int] = None
    rate_plan_detail_id: Optional[int] = None
    precio_unitario: Optional[float] = None
    precio_total: Optional[float] = None
    bonificacion_piloto: Optional[float] = None
    pricing_version: Optional[int] = None

    created_by_user_id: Optional[int] = None
    created_by_username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PilotCreate(BaseModel):
    nombre: str


class PilotResponse(BaseModel):
    id: int
    nombre: str
    activo: str
    created_at: datetime

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


class ClientResponse(ClientCreate):
    id: int
    activo: str

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


class RouteResponse(RouteCreate):
    id: int
    activo: str

    class Config:
        from_attributes = True


class VehicleTypeCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    ejes: Optional[int] = None
    capacidad: Optional[float] = None


class VehicleTypeResponse(VehicleTypeCreate):
    id: int
    activo: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChargeTypeCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class ChargeTypeResponse(ChargeTypeCreate):
    id: int
    activo: str
    created_at: datetime

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
    vehicle_type_id: Optional[int] = None
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


class FuelPriceCreate(BaseModel):
    fecha: date
    precio_galon: float
    fuente: Optional[str] = None
    observaciones: Optional[str] = None


class FuelPriceResponse(FuelPriceCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RatePlanCreate(BaseModel):
    codigo: str
    nombre: str
    scope: Optional[str] = "CLIENT"
    client_id: Optional[int] = None
    route_id: Optional[int] = None
    vehicle_type_id: int
    charge_type_id: int
    producto: Optional[str] = None
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    moneda: Optional[str] = "GTQ"
    version: Optional[int] = 1
    estado: Optional[str] = "ACTIVO"
    observaciones: Optional[str] = None


class RatePlanResponse(RatePlanCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RatePlanDetailCreate(BaseModel):
    rate_plan_id: int
    combustible_min: Optional[float] = None
    combustible_max: Optional[float] = None
    peso_min: Optional[float] = None
    peso_max: Optional[float] = None
    precio_unitario: float
    bonificacion_piloto: Optional[float] = None
    margen_estimado: Optional[float] = None


class RatePlanDetailResponse(RatePlanDetailCreate):
    id: int
    activo: str
    created_at: datetime

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

class ExpenseCategoryCreate(BaseModel):
    nombre: str
    tipo: str = "OPERATIVO"
    requiere_camion: str = "NO"
    afecta_estado_resultados: str = "SI"


class ExpenseCategoryResponse(BaseModel):
    id: int
    nombre: str
    tipo: str
    requiere_camion: str
    afecta_estado_resultados: str
    activo: str
    created_at: datetime

    class Config:
        from_attributes = True

class ExpenseCreate(BaseModel):
    expense_category_id: int
    truck_id: Optional[int] = None
    descripcion: Optional[str] = None
    documento: Optional[str] = None
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    periodicidad: str = "UNICO"
    meses_prorrateo: int = 1
    monto: float


class ExpenseUpdate(BaseModel):
    expense_category_id: Optional[int] = None
    truck_id: Optional[int] = None
    descripcion: Optional[str] = None
    documento: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    periodicidad: Optional[str] = None
    meses_prorrateo: Optional[int] = None
    monto: Optional[float] = None


class ExpenseResponse(ExpenseCreate):
    id: int
    activo: str
    created_by_user_id: Optional[int] = None
    created_by_username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TariffImportHistoryResponse(BaseModel):
    id: int
    archivo: Optional[str] = None
    usuario: Optional[str] = None
    version: Optional[str] = None
    filas: int
    rutas_creadas: int
    tarifarios_creados: int
    rangos_creados: int
    viajes_actualizados: int
    errores: Optional[str] = None
    estado: str
    fecha_importacion: datetime

    class Config:
        from_attributes = True