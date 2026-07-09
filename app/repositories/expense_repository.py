from sqlalchemy.orm import Session

from models import Expense


class ExpenseRepository:

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(Expense)
            .filter(Expense.activo == "SI")
            .order_by(Expense.fecha_inicio.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, item_id: int):
        return (
            db.query(Expense)
            .filter(Expense.id == item_id)
            .first()
        )

    @staticmethod
    def create(db: Session, item: Expense):
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update(db: Session):
        db.commit()