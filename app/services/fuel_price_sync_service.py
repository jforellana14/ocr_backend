from datetime import date, timedelta
from typing import Iterable

from sqlalchemy.orm import Session

from models import FuelPrice


class FuelPriceSyncService:

    @staticmethod
    def upsert_price(
        db: Session,
        price_date: date,
        price: float,
        source: str = "MEM",
        notes: str | None = None,
        commit: bool = True,
    ) -> FuelPrice:
        if price <= 0:
            raise ValueError("El precio del combustible debe ser mayor a cero.")

        item = (
            db.query(FuelPrice)
            .filter(FuelPrice.fecha == price_date)
            .first()
        )

        if item:
            item.precio_galon = round(float(price), 2)
            item.fuente = source
            item.observaciones = notes
        else:
            item = FuelPrice(
                fecha=price_date,
                precio_galon=round(float(price), 2),
                fuente=source,
                observaciones=notes,
            )
            db.add(item)

        if commit:
            db.commit()
            db.refresh(item)
        else:
            db.flush()

        return item

    @staticmethod
    def fill_date_range(
        db: Session,
        start_date: date,
        end_date: date,
        price: float,
        source: str,
        notes: str | None = None,
    ) -> int:
        if end_date < start_date:
            raise ValueError("La fecha final no puede ser menor a la inicial.")

        current = start_date
        affected = 0

        while current <= end_date:
            FuelPriceSyncService.upsert_price(
                db=db,
                price_date=current,
                price=price,
                source=source,
                notes=notes,
                commit=False,
            )
            affected += 1
            current += timedelta(days=1)

        db.commit()
        return affected

    @staticmethod
    def import_periods(
        db: Session,
        periods: Iterable[dict],
    ) -> dict:
        days_saved = 0
        errors = []

        try:
            for index, period in enumerate(periods, start=1):
                try:
                    start_date = date.fromisoformat(period["fecha_inicio"])
                    end_date = date.fromisoformat(period["fecha_fin"])
                    price = float(period["precio_galon"])

                    days_saved += FuelPriceSyncService.fill_date_range(
                        db=db,
                        start_date=start_date,
                        end_date=end_date,
                        price=price,
                        source=period.get("fuente", "MEM"),
                        notes=period.get("observaciones"),
                    )
                except Exception as exc:
                    errors.append({
                        "fila": index,
                        "motivo": str(exc),
                    })

            return {
                "dias_guardados": days_saved,
                "errores": errors,
            }

        except Exception:
            db.rollback()
            raise