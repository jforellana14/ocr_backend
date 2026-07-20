from app.repositories.base_repository import BaseRepository
from models import FuelPrice


class FuelPriceRepository(BaseRepository):

    model = FuelPrice

    @classmethod
    def get_by_date(cls, db, fecha):
        return (
            db.query(cls.model)
            .filter(cls.model.fecha == fecha)
            .first()
        )