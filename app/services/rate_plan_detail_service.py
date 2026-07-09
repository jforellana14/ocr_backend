from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import RatePlanDetail
from schemas import RatePlanDetailCreate
from app.repositories.rate_plan_detail_repository import RatePlanDetailRepository
from app.repositories.rate_plan_repository import RatePlanRepository


class RatePlanDetailService:

    @staticmethod
    def get_by_rate_plan(db: Session, rate_plan_id: int):
        return RatePlanDetailRepository.get_by_rate_plan(
            db,
            rate_plan_id
        )

    @staticmethod
    def create(db: Session, payload: RatePlanDetailCreate):

        plan = RatePlanRepository.get_by_id(
            db,
            payload.rate_plan_id
        )

        if not plan:
            raise HTTPException(
                status_code=404,
                detail="El tarifario no existe."
            )

        if (
            payload.combustible_min is not None
            and payload.combustible_max is not None
            and payload.combustible_min > payload.combustible_max
        ):
            raise HTTPException(
                status_code=400,
                detail="El rango de combustible es inválido."
            )

        if (
            payload.peso_min is not None
            and payload.peso_max is not None
            and payload.peso_min > payload.peso_max
        ):
            raise HTTPException(
                status_code=400,
                detail="El rango de peso es inválido."
            )

        item = RatePlanDetail(
            rate_plan_id=payload.rate_plan_id,
            combustible_min=payload.combustible_min,
            combustible_max=payload.combustible_max,
            peso_min=payload.peso_min,
            peso_max=payload.peso_max,
            precio_unitario=payload.precio_unitario,
            bonificacion_piloto=payload.bonificacion_piloto,
            margen_estimado=payload.margen_estimado,
            activo="SI"
        )

        return RatePlanDetailRepository.create(
            db,
            item
        )

    @staticmethod
    def delete(db: Session, item_id: int):

        item = RatePlanDetailRepository.get_by_id(
            db,
            item_id
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Detalle no encontrado."
            )

        item.activo = "NO"

        RatePlanDetailRepository.update(db)

        return {
            "message": "Detalle desactivado correctamente."
        }