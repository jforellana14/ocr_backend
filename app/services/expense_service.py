from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Expense, ExpenseCategory
from schemas import ExpenseCreate
from app.repositories.expense_repository import ExpenseRepository


class ExpenseService:

    @staticmethod
    def get_all(db: Session):
        return ExpenseRepository.get_all(db)

    @staticmethod
    def get_by_id(db: Session, item_id: int):
        item = ExpenseRepository.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Gasto no encontrado."
            )

        return item

    @staticmethod
    def create(
        db: Session,
        payload: ExpenseCreate,
        current_user
    ):

        category = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.id == payload.expense_category_id
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="La categoría no existe."
            )

        if (
            category.requiere_camion == "SI"
            and payload.truck_id is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Esta categoría requiere seleccionar un camión."
            )

        if (
            category.requiere_camion == "NO"
            and payload.truck_id is not None
        ):
            raise HTTPException(
                status_code=400,
                detail="Esta categoría no permite seleccionar un camión."
            )

        item = Expense(
            **payload.model_dump(),
            created_by_user_id=current_user.id,
            created_by_username=current_user.username
        )

        return ExpenseRepository.create(
            db,
            item
        )

    @staticmethod
    def delete(
        db: Session,
        item_id: int
    ):

        item = ExpenseRepository.get_by_id(
            db,
            item_id
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Gasto no encontrado."
            )

        item.activo = "NO"

        ExpenseRepository.update(db)

        return {
            "message": "Gasto eliminado correctamente."
        }