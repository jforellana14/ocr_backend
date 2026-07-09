from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import FuelPriceCreate, FuelPriceResponse
from auth import get_current_user, require_roles
from app.services.fuel_price_service import FuelPriceService


router = APIRouter(
    prefix="/fuel-prices",
    tags=["Fuel Prices"]
)


@router.get("", response_model=list[FuelPriceResponse])
def get_fuel_prices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return FuelPriceService.get_all(db)


@router.post("", response_model=FuelPriceResponse)
def create_fuel_price(
    payload: FuelPriceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return FuelPriceService.create(db, payload)


@router.delete("/{item_id}")
def delete_fuel_price(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return FuelPriceService.delete(db, item_id)