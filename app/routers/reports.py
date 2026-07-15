from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import get_current_user
from app.services.income_statement_service import IncomeStatementService


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/income-statement")
def income_statement(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mes inválido.")
    return IncomeStatementService.get_month(db, year, month)


@router.get("/dashboard-summary")
def dashboard_summary(
    date_from: date,
    date_to: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if date_to < date_from:
        raise HTTPException(
            status_code=400,
            detail="La fecha final no puede ser menor que la fecha inicial.",
        )
    return IncomeStatementService.get_range(db, date_from, date_to)
