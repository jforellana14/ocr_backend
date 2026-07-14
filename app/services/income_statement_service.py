from calendar import monthrange
from datetime import date

from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from models import Document, Expense, ExpenseCategory


class IncomeStatementService:

    @staticmethod
    def _expense_applies_to_month(
        expense: Expense,
        period_start: date,
        period_end: date,
    ) -> bool:
        if expense.activo != "SI":
            return False

        start = expense.fecha_inicio
        end = expense.fecha_fin
        frequency = (expense.periodicidad or "UNICO").upper()

        if not start:
            return False

        if frequency == "UNICO":
            return period_start <= start <= period_end

        if start > period_end:
            return False

        if end and end < period_start:
            return False

        months_difference = (
            (period_start.year - start.year) * 12
            + period_start.month
            - start.month
        )

        if months_difference < 0:
            return False

        intervals = {
            "MENSUAL": 1,
            "BIMESTRAL": 2,
            "TRIMESTRAL": 3,
            "SEMESTRAL": 6,
            "ANUAL": 12,
        }

        interval = intervals.get(frequency)

        if interval is None:
            return False

        return months_difference % interval == 0

    @staticmethod
    def get_month(
        db: Session,
        year: int,
        month: int,
    ):
        period_start = date(year, month, 1)
        period_end = date(
            year,
            month,
            monthrange(year, month)[1],
        )

        ingresos = (
            db.query(
                func.coalesce(
                    func.sum(Document.precio_total),
                    0,
                )
            )
            .filter(Document.fecha >= period_start)
            .filter(Document.fecha <= period_end)
            .scalar()
        )

        bonificaciones = (
            db.query(
                func.coalesce(
                    func.sum(Document.bonificacion_piloto),
                    0,
                )
            )
            .filter(Document.fecha >= period_start)
            .filter(Document.fecha <= period_end)
            .scalar()
        )

        expenses = (
            db.query(Expense)
            .outerjoin(
                ExpenseCategory,
                Expense.expense_category_id
                == ExpenseCategory.id,
            )
            .filter(Expense.activo == "SI")
            .filter(
                or_(
                    ExpenseCategory.id.is_(None),
                    ExpenseCategory.afecta_estado_resultados == "SI",
                )
            )
            .all()
        )

        gastos = 0.0

        for expense in expenses:
            if IncomeStatementService._expense_applies_to_month(
                expense=expense,
                period_start=period_start,
                period_end=period_end,
            ):
                gastos += float(expense.monto or 0)

        utilidad = (
            float(ingresos or 0)
            - float(bonificaciones or 0)
            - gastos
        )

        return {
            "periodo": f"{year}-{month:02d}",
            "ingresos": float(ingresos or 0),
            "bonificaciones": float(
                bonificaciones or 0
            ),
            "gastos": round(gastos, 2),
            "utilidad": round(utilidad, 2),
        }