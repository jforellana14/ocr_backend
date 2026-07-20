from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.dashboard_service import DashboardService
from app.services.income_statement_service import IncomeStatementService
from auth import get_current_user
from database import get_db
from models import User

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard-summary")
def dashboard_summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="La fecha final no puede ser menor que la inicial.")
    return DashboardService.get_range(db, date_from, date_to)


@router.get("/income-statement")
def income_statement(
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if date_from is not None or date_to is not None:
        if date_from is None or date_to is None:
            raise HTTPException(status_code=400, detail="Debe indicar date_from y date_to juntos.")
        if date_to < date_from:
            raise HTTPException(status_code=400, detail="Rango de fechas inválido.")
        return IncomeStatementService.get_range(db, date_from, date_to)

    if year is None or month is None:
        raise HTTPException(status_code=400, detail="Indique year/month o date_from/date_to válidos.")
    return IncomeStatementService.get_month(db, year, month)
