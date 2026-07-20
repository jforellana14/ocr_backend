from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import RatePlanCreate, RatePlanResponse
from auth import get_current_user, require_roles
from app.services.rate_plan_service import RatePlanService


router = APIRouter(
    prefix="/rate-plans",
    tags=["Rate Plans"]
)


@router.get("", response_model=list[RatePlanResponse])
def get_rate_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return RatePlanService.get_all(db)


@router.post("", response_model=RatePlanResponse)
def create_rate_plan(
    payload: RatePlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return RatePlanService.create(db, payload)


@router.delete("/{item_id}")
def delete_rate_plan(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return RatePlanService.delete(db, item_id)