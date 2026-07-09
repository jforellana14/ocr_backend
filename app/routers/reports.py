from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import get_current_user
from app.services.income_statement_service import IncomeStatementService


router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.get("/income-statement")
def income_statement(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return IncomeStatementService.get_month(
        db,
        year,
        month
    )