from __future__ import annotations

from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.dashboard_service import DashboardService
from app.services.income_statement_service import IncomeStatementService
from app.services.profitability_service import ProfitabilityService
from auth import get_current_user
from database import get_db
from models import User

router = APIRouter(prefix="/finance", tags=["Finance"])


def _validate_range(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise HTTPException(
            status_code=400,
            detail="La fecha final no puede ser menor que la inicial.",
        )


def _profitability_response(
    service_method: Callable[[Session, date, date], dict[str, Any]],
    db: Session,
    date_from: date,
    date_to: date,
) -> dict[str, Any]:
    """Ejecuta un reporte de rentabilidad y normaliza errores de validación."""

    _validate_range(date_from, date_to)
    try:
        return service_method(db, date_from, date_to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard")
def dashboard(
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_range(date_from, date_to)
    return DashboardService.get_range(db, date_from, date_to)


@router.get("/income-statement")
def income_statement(
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if date_from is not None or date_to is not None:
        if date_from is None or date_to is None:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar date_from y date_to juntos.",
            )
        _validate_range(date_from, date_to)
        return IncomeStatementService.get_range(db, date_from, date_to)

    if year is None or month is None:
        raise HTTPException(
            status_code=400,
            detail="Indique year/month o date_from/date_to válidos.",
        )
    return IncomeStatementService.get_month(db, year, month)


@router.get("/profitability/client")
def profitability_by_client(
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _profitability_response(
        ProfitabilityService.by_client,
        db,
        date_from,
        date_to,
    )


@router.get("/profitability/driver")
def profitability_by_driver(
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _profitability_response(
        ProfitabilityService.by_driver,
        db,
        date_from,
        date_to,
    )


@router.get("/profitability/truck")
def profitability_by_truck(
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _profitability_response(
        ProfitabilityService.by_truck,
        db,
        date_from,
        date_to,
    )


@router.get("/profitability/route")
def profitability_by_route(
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _profitability_response(
        ProfitabilityService.by_route,
        db,
        date_from,
        date_to,
    )


@router.get("/profitability/product")
def profitability_by_product(
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _profitability_response(
        ProfitabilityService.by_product,
        db,
        date_from,
        date_to,
    )


@router.get("/profitability/{dimension}")
def profitability_by_dimension(
    dimension: str,
    date_from: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    date_to: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Endpoint genérico para las dimensiones admitidas por el servicio."""

    _validate_range(date_from, date_to)
    try:
        return ProfitabilityService.get_by_dimension(
            db,
            date_from,
            date_to,
            dimension,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health")
def finance_health(current_user: User = Depends(get_current_user)):
    return {
        "status": "ok",
        "engine": "FinancialEngine",
        "single_source_of_truth": True,
        "version": "1.1.0",
        "profitability": {
            "enabled": True,
            "modes": ["operating", "enterprise"],
            "dimensions": sorted(ProfitabilityService.DIMENSIONS),
        },
    }
