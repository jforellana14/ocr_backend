from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import VehicleTypeCreate, VehicleTypeResponse
from auth import get_current_user, require_roles
from app.services.vehicle_type_service import VehicleTypeService


router = APIRouter(
    prefix="/vehicle-types",
    tags=["Vehicle Types"]
)


@router.get("", response_model=list[VehicleTypeResponse])
def get_vehicle_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return VehicleTypeService.get_all(db)


@router.post("", response_model=VehicleTypeResponse)
def create_vehicle_type(
    payload: VehicleTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return VehicleTypeService.create(db, payload)


@router.delete("/{item_id}")
def delete_vehicle_type(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return VehicleTypeService.delete(db, item_id)