from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import FuelPrice
from app.repositories.fuel_price_repository import FuelPriceRepository
from schemas import FuelPriceCreate


class FuelPriceService:

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(FuelPrice)
            .order_by(FuelPrice.fecha.desc())
            .all()
        )

    @staticmethod
    def create(db: Session, payload: FuelPriceCreate):

        exists = (
            db.query(FuelPrice)
            .filter(FuelPrice.fecha == payload.fecha)
            .first()
        )

        if exists:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un precio para esa fecha."
            )

        item = FuelPrice(
            fecha=payload.fecha,
            precio_galon=payload.precio_galon,
            fuente=payload.fuente,
            observaciones=payload.observaciones
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        return item

    @staticmethod
    def delete(db: Session, item_id: int):

        item = (
            db.query(FuelPrice)
            .filter(FuelPrice.id == item_id)
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Precio no encontrado."
            )

        db.delete(item)
        db.commit()

        return {
            "message": "Precio eliminado correctamente."
        }