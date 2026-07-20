from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from models import Document, Expense, FinancialSettings


class FinancialRepository:
    """Acceso único a los datos requeridos por el motor financiero.

    La columna ``Document.fecha`` continúa siendo texto por compatibilidad con la
    aplicación móvil. El repositorio limita primero los registros ISO cuando es
    posible y el motor realiza la validación final del rango para admitir fechas
    históricas en otros formatos.
    """

    @staticmethod
    def documents_for_period(db: Session, start: date, end: date) -> list[Document]:
        iso_start = start.isoformat()
        iso_end = end.isoformat()
        return (
            db.query(Document)
            .filter(
                or_(
                    Document.fecha.between(iso_start, iso_end),
                    Document.fecha.like("%/%"),
                    Document.fecha.like("%-%-%"),
                )
            )
            .all()
        )

    @staticmethod
    def active_expenses_for_period(db: Session, start: date, end: date) -> list[Expense]:
        return (
            db.query(Expense)
            .options(joinedload(Expense.category))
            .filter(
                Expense.activo == "SI",
                Expense.fecha_inicio <= end,
                or_(Expense.fecha_fin.is_(None), Expense.fecha_fin >= start),
            )
            .all()
        )

    @staticmethod
    def settings(db: Session) -> FinancialSettings:
        settings = db.query(FinancialSettings).order_by(FinancialSettings.id.asc()).first()
        if settings is None:
            settings = FinancialSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    # Alias temporales para compatibilidad con código externo previo.
    @staticmethod
    def documents(db: Session) -> Iterable[Document]:
        return db.query(Document).all()

    @staticmethod
    def active_expenses(db: Session) -> Iterable[Expense]:
        return (
            db.query(Expense)
            .options(joinedload(Expense.category))
            .filter(Expense.activo == "SI")
            .all()
        )
