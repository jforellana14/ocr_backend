from app.repositories.base_repository import BaseRepository
from models import RatePlanDetail


class RatePlanDetailRepository(BaseRepository):

    model = RatePlanDetail

    @classmethod
    def get_by_rate_plan(cls, db, rate_plan_id: int):
        return (
            db.query(cls.model)
            .filter(cls.model.rate_plan_id == rate_plan_id)
            .filter(cls.model.activo == "SI")
            .order_by(cls.model.combustible_min.asc(), cls.model.peso_min.asc())
            .all()
        )