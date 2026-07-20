from sqlalchemy.orm import Session

from models import ExpenseCategory


class ExpenseCategoryRepository:

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(ExpenseCategory)
            .order_by(ExpenseCategory.nombre)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, item_id: int):
        return (
            db.query(ExpenseCategory)
            .filter(ExpenseCategory.id == item_id)
            .first()
        )

    @staticmethod
    def create(db: Session, item: ExpenseCategory):
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update(db: Session):
        db.commit()

    @staticmethod
    def delete(db: Session, item: ExpenseCategory):
        db.delete(item)
        db.commit()