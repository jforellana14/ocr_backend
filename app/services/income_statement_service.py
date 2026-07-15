from datetime import date

from sqlalchemy.orm import Session

from app.services.financial_engine import FinancialEngine


class IncomeStatementService:
    @staticmethod
    def get_month(db: Session, year: int, month: int):
        return FinancialEngine.get_month(db, year, month)

    @staticmethod
    def get_range(db: Session, date_from: date, date_to: date):
        return FinancialEngine.get_range(db, date_from, date_to)
