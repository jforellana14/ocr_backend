from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from models import Document, Expense


class IncomeStatementService:

    @staticmethod
    def get_month(db: Session, year: int, month: int):

        ingresos = (
            db.query(
                func.coalesce(
                    func.sum(Document.precio_total),
                    0
                )
            )
            .filter(extract("year", Document.created_at) == year)
            .filter(extract("month", Document.created_at) == month)
            .scalar()
        )

        bonificaciones = (
            db.query(
                func.coalesce(
                    func.sum(Document.bonificacion_piloto),
                    0
                )
            )
            .filter(extract("year", Document.created_at) == year)
            .filter(extract("month", Document.created_at) == month)
            .scalar()
        )

        gastos = (
            db.query(
                func.coalesce(
                    func.sum(Expense.monto),
                    0
                )
            )
            .filter(Expense.activo == "SI")
            .filter(extract("year", Expense.fecha_inicio) == year)
            .filter(extract("month", Expense.fecha_inicio) == month)
            .scalar()
        )

        utilidad = ingresos - bonificaciones - gastos

        return {
            "periodo": f"{year}-{month:02d}",
            "ingresos": float(ingresos),
            "bonificaciones": float(bonificaciones),
            "gastos": float(gastos),
            "utilidad": float(utilidad),
        }