from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import FuelStation
from schemas import FuelStationCreate
from app.repositories.fuel_station_repository import FuelStationRepository


class FuelStationService:

    @staticmethod
    def get_all(db: Session):
        return FuelStationRepository.get_all(db)

    @staticmethod
    def get_by_id(db: Session, item_id: int):
        item = FuelStationRepository.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="FuelStation no encontrado."
            )

        return item

    @staticmethod
    def create(db: Session, payload: FuelStationCreate):
        item = FuelStation(**payload.model_dump())
        return FuelStationRepository.create(db, item)

    @staticmethod
    def delete(db: Session, item_id: int):
        item = FuelStationRepository.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="FuelStation no encontrado."
            )

        FuelStationRepository.delete(db, item)

        return {
            "message": "FuelStation eliminado correctamente."
        }
