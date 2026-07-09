from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import VehicleType
from schemas import VehicleTypeCreate


class VehicleTypeService:

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(VehicleType)
            .filter(VehicleType.activo == "SI")
            .order_by(VehicleType.nombre.asc())
            .all()
        )

    @staticmethod
    def create(db: Session, payload: VehicleTypeCreate):

        exists = (
            db.query(VehicleType)
            .filter(VehicleType.nombre == payload.nombre.upper().strip())
            .first()
        )

        if exists:
            raise HTTPException(
                status_code=400,
                detail="El tipo de vehículo ya existe."
            )

        item = VehicleType(
            nombre=payload.nombre.upper().strip(),
            descripcion=payload.descripcion,
            ejes=payload.ejes,
            capacidad=payload.capacidad,
            activo="SI"
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        return item

    @staticmethod
    def delete(db: Session, item_id: int):

        item = (
            db.query(VehicleType)
            .filter(VehicleType.id == item_id)
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Tipo de vehículo no encontrado."
            )

        item.activo = "NO"

        db.commit()

        return {
            "message": "Tipo de vehículo desactivado."
        }