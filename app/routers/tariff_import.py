from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User
from auth import require_roles
from app.services.tariff_import_service import (
    import_tariff_rows_and_update_documents,
)


router = APIRouter(
    prefix="/admin/tariff-import",
    tags=["Admin Tariff Import"]
)


@router.post("")
def import_tariff(
    rows: List[dict],
    vehicle_type_id: int,
    charge_type_id: int = 1,
    force_recalculate: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return import_tariff_rows_and_update_documents(
        db=db,
        rows=rows,
        vehicle_type_id=vehicle_type_id,
        charge_type_id=charge_type_id,
        force_recalculate=force_recalculate
    )