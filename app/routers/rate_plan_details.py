from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import RatePlanDetailCreate, RatePlanDetailResponse
from auth import get_current_user, require_roles
from app.services.rate_plan_detail_service import RatePlanDetailService


router = APIRouter(
    prefix="/rate-plan-details",
    tags=["Rate Plan Details"]
)


@router.get("/{rate_plan_id}", response_model=list[RatePlanDetailResponse])
def get_rate_plan_details(
    rate_plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return RatePlanDetailService.get_by_rate_plan(db, rate_plan_id)


@router.post("", response_model=RatePlanDetailResponse)
def create_rate_plan_detail(
    payload: RatePlanDetailCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return RatePlanDetailService.create(db, payload)


@router.delete("/{item_id}")
def delete_rate_plan_detail(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return RatePlanDetailService.delete(db, item_id)