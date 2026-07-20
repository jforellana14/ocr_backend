from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import FuelStationCreate, FuelStationResponse
from auth import get_current_user, require_roles
from app.services.fuel_station_service import FuelStationService


router = APIRouter(
    prefix="/fuel-station",
    tags=["FuelStation"]
)


@router.get("", response_model=list[FuelStationResponse])
def get_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return FuelStationService.get_all(db)


@router.get("/{item_id}", response_model=FuelStationResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return FuelStationService.get_by_id(db, item_id)


@router.post("", response_model=FuelStationResponse)
def create_item(
    payload: FuelStationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return FuelStationService.create(db, payload)


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return FuelStationService.delete(db, item_id)
