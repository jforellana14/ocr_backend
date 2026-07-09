from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import ChargeType
from schemas import ChargeTypeCreate


class ChargeTypeService:

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(ChargeType)
            .filter(ChargeType.activo == "SI")
            .order_by(ChargeType.nombre.asc())
            .all()
        )

    @staticmethod
    def create(db: Session, payload: ChargeTypeCreate):

        exists = (
            db.query(ChargeType)
            .filter(ChargeType.nombre == payload.nombre.upper().strip())
            .first()
        )

        if exists:
            raise HTTPException(
                status_code=400,
                detail="El tipo de cobro ya existe."
            )

        item = ChargeType(
            nombre=payload.nombre.upper().strip(),
            descripcion=payload.descripcion,
            activo="SI"
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        return item

    @staticmethod
    def delete(db: Session, item_id: int):

        item = (
            db.query(ChargeType)
            .filter(ChargeType.id == item_id)
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Tipo de cobro no encontrado."
            )

        item.activo = "NO"

        db.commit()

        return {
            "message": "Tipo de cobro desactivado."
        }