from __future__ import annotations

import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from database import SessionLocal
from app.services.fuel_price_sync_service import (
    FuelPriceSyncService,
)
from app.services.mem_fuel_price_provider import (
    MemFuelPriceProvider,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> int:
    db = SessionLocal()

    try:
        logging.info(
            "Consultando precio del diésel mediante ScrapingBee."
        )

        result = (
            MemFuelPriceProvider
            .fetch_current_diesel_price()
        )

        notes = (
            "Sincronización automática mediante ScrapingBee. "
            f"Fuente oficial: {result.fuente}. "
            f"Vigencia: "
            f"{result.vigencia_inicio or 'N/D'} al "
            f"{result.vigencia_fin or 'N/D'}."
        )

        item = FuelPriceSyncService.upsert_price(
            db=db,
            price_date=result.fecha,
            price=result.precio_diesel,
            source="MEM / SCRAPINGBEE",
            notes=notes,
        )

        logging.info(
            "Precio guardado correctamente: "
            "fecha=%s precio=Q%.2f id=%s",
            item.fecha,
            item.precio_galon,
            item.id,
        )

        return 0

    except RuntimeError as exc:
        db.rollback()

        logging.error(
            "No fue posible actualizar el diésel: %s",
            exc,
        )

        return 1

    except Exception:
        db.rollback()

        logging.exception(
            "Falló la actualización automática "
            "del combustible."
        )

        return 1

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())