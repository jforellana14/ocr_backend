from app.repositories.base_repository import BaseRepository
from models import RatePlan


class RatePlanRepository(BaseRepository):

    model = RatePlan

    @classmethod
    def get_active(cls, db):
        return (
            db.query(cls.model)
            .filter(cls.model.estado == "ACTIVO")
            .order_by(cls.model.fecha_inicio.desc())
            .all()
        )

    @classmethod
    def get_by_code(cls, db, codigo):
        return (
            db.query(cls.model)
            .filter(cls.model.codigo == codigo)
            .first()
        )