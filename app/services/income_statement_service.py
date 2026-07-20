<<<<<<< HEAD
from __future__ import annotations

=======
>>>>>>> cf0e5c16d051ba9647f1ae05a2253b919f8c22f3
from datetime import date

from sqlalchemy.orm import Session

from app.services.financial_engine import FinancialEngine


class IncomeStatementService:
<<<<<<< HEAD
    """Adaptador contable; comparte exactamente el mismo resultado del motor."""

    @staticmethod
    def get_range(db: Session, start: date, end: date) -> dict:
        return FinancialEngine.get_range(db, start, end)

    @staticmethod
    def get_month(db: Session, year: int, month: int) -> dict:
        return FinancialEngine.get_month(db, year, month)
=======
    @staticmethod
    def get_month(db: Session, year: int, month: int):
        return FinancialEngine.get_month(db, year, month)

    @staticmethod
    def get_range(db: Session, date_from: date, date_to: date):
        return FinancialEngine.get_range(db, date_from, date_to)
>>>>>>> cf0e5c16d051ba9647f1ae05a2253b919f8c22f3
