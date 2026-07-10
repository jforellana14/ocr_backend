import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from database import SessionLocal
from app.services.fuel_price_sync_service import FuelPriceSyncService
from app.services.mem_fuel_price_provider import MemFuelPriceProvider


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> None:
    db = SessionLocal()

    try:
        result = MemFuelPriceProvider.fetch_current_diesel_price()

        item = FuelPriceSyncService.upsert_price(
            db=db,
            price_date=result.fecha,
            price=result.precio_diesel,
            source="MEM",
            notes=f"Sincronización automática: {result.fuente}",
        )

        logging.info(
            "Precio guardado: fecha=%s precio=Q%.2f id=%s",
            item.fecha,
            item.precio_galon,
            item.id,
        )

    except Exception:
        db.rollback()
        logging.exception(
            "Falló la actualización automática del combustible."
        )
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()