from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import RatePlan
from schemas import RatePlanCreate
from app.repositories.rate_plan_repository import RatePlanRepository


class RatePlanService:

    @staticmethod
    def get_all(db: Session):
        return RatePlanRepository.get_active(db)

    @staticmethod
    def create(db: Session, payload: RatePlanCreate):

        exists = RatePlanRepository.get_by_code(
            db,
            payload.codigo.upper().strip()
        )

        if exists:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un tarifario con ese código."
            )

        item = RatePlan(
            codigo=payload.codigo.upper().strip(),
            nombre=payload.nombre.upper().strip(),
            scope=payload.scope,
            client_id=payload.client_id,
            route_id=payload.route_id,
            vehicle_type_id=payload.vehicle_type_id,
            charge_type_id=payload.charge_type_id,
            producto=payload.producto,
            fecha_inicio=payload.fecha_inicio,
            fecha_fin=payload.fecha_fin,
            moneda=payload.moneda,
            version=payload.version,
            estado=payload.estado,
            observaciones=payload.observaciones
        )

        return RatePlanRepository.create(db, item)

    @staticmethod
    def delete(db: Session, item_id: int):

        item = RatePlanRepository.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Tarifario no encontrado."
            )

        item.estado = "INACTIVO"

        RatePlanRepository.update(db)

        return {
            "message": "Tarifario desactivado correctamente."
        }