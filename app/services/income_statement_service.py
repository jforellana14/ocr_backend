from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.services.financial_engine import FinancialEngine


class IncomeStatementService:
    """Adaptador contable; comparte exactamente el mismo resultado del motor."""

    @staticmethod
    def get_range(db: Session, start: date, end: date) -> dict:
        return FinancialEngine.get_range(db, start, end)

    @staticmethod
    def get_month(db: Session, year: int, month: int) -> dict:
        return FinancialEngine.get_month(db, year, month)
