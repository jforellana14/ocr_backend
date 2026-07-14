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
        payload: ExpenseCategoryCreate,
    ):
        nombre = payload.nombre.strip().upper()

        if not nombre:
            raise HTTPException(
                status_code=400,
                detail="El nombre de la categoría es obligatorio.",
            )

        exists = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.nombre.ilike(nombre)
            )
            .first()
        )

        if exists:
            if exists.activo == "NO":
                exists.activo = "SI"
                exists.tipo = payload.tipo.strip().upper()
                exists.requiere_camion = (
                    payload.requiere_camion.strip().upper()
                )
                exists.afecta_estado_resultados = (
                    payload.afecta_estado_resultados.strip().upper()
                )

                db.commit()
                db.refresh(exists)

                return exists

            raise HTTPException(
                status_code=400,
                detail=f"La categoría {nombre} ya existe.",
            )

        item = ExpenseCategory(
            nombre=nombre,
            tipo=payload.tipo.strip().upper(),
            requiere_camion=payload.requiere_camion.strip().upper(),
            afecta_estado_resultados=(
                payload.afecta_estado_resultados.strip().upper()
            ),
            activo="SI",
        )

        return ExpenseCategoryRepository.create(
            db,
            item,
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