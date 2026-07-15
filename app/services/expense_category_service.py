from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import ExpenseCategory
from schemas import ExpenseCategoryCreate
from app.repositories.expense_category_repository import (
    ExpenseCategoryRepository,
)


class ExpenseCategoryService:

    @staticmethod
    def get_all(db: Session):
        return ExpenseCategoryRepository.get_all(db)

    @staticmethod
    def get_by_id(db: Session, item_id: int):
        item = ExpenseCategoryRepository.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Categoría no encontrada."
            )

        return item

    @staticmethod
    def create(
        db: Session,
        payload: ExpenseCategoryCreate
    ):
        exists = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.nombre == payload.nombre
            )
            .first()
        )

        if exists:
            raise HTTPException(
                status_code=400,
                detail="La categoría ya existe."
            )

        item = ExpenseCategory(
            **payload.model_dump()
        )

        return ExpenseCategoryRepository.create(
            db,
            item
        )

    @staticmethod
    def delete(
        db: Session,
        item_id: int
    ):
        item = ExpenseCategoryRepository.get_by_id(
            db,
            item_id
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Categoría no encontrada."
            )

        item.activo = "NO"

        ExpenseCategoryRepository.update(db)

        return {
            "message": "Categoría eliminada correctamente."
        }