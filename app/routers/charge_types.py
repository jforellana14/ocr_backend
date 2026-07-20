from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import ChargeTypeCreate, ChargeTypeResponse
from auth import get_current_user, require_roles
from app.services.charge_type_service import ChargeTypeService


router = APIRouter(
    prefix="/charge-types",
    tags=["Charge Types"]
)


@router.get("", response_model=list[ChargeTypeResponse])
def get_charge_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ChargeTypeService.get_all(db)


@router.post("", response_model=ChargeTypeResponse)
def create_charge_type(
    payload: ChargeTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return ChargeTypeService.create(db, payload)


@router.delete("/{item_id}")
def delete_charge_type(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return ChargeTypeService.delete(db, item_id)