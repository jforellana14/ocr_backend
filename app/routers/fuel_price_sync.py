from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import require_roles
from database import get_db
from models import User
from app.services.fuel_price_sync_service import FuelPriceSyncService


router = APIRouter(
    prefix="/admin/fuel-price-sync",
    tags=["Admin Fuel Price Sync"],
)


class FuelPricePeriod(BaseModel):
    fecha_inicio: str
    fecha_fin: str
    precio_galon: float = Field(gt=0)
    fuente: str = "MEM"
    observaciones: str | None = None


class FuelPriceBackfillRequest(BaseModel):
    periodos: list[FuelPricePeriod]


@router.post("/backfill")
def backfill_fuel_prices(
    payload: FuelPriceBackfillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    if not payload.periodos:
        raise HTTPException(
            status_code=400,
            detail="Debe enviar al menos un período.",
        )

    return FuelPriceSyncService.import_periods(
        db=db,
        periods=[
            period.model_dump()
            for period in payload.periodos
        ],
    )