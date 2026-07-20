from app.repositories.base_repository import BaseRepository
from models import FuelStation


class FuelStationRepository(BaseRepository):

    model = FuelStation
