from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import FuelPrice
from schemas import FuelPriceCreate
from app.repositories.fuel_price_repository import FuelPriceRepository


class FuelPriceService:

    @staticmethod
    def get_all(db: Session):
        return FuelPriceRepository.get_all(db)

    @staticmethod
    def create(db: Session, payload: FuelPriceCreate):
        exists = FuelPriceRepository.get_by_date(db, payload.fecha)

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

        return FuelPriceRepository.create(db, item)

    @staticmethod
    def delete(db: Session, item_id: int):
        item = FuelPriceRepository.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Precio no encontrado."
            )

        FuelPriceRepository.delete(db, item)

        return {"message": "Precio eliminado correctamente."}