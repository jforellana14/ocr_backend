import re
from dataclasses import dataclass
from datetime import date

import httpx


MEM_URL = "https://mem.gob.gt/precios-petroleo-combustibles/"


@dataclass
class MemFuelPriceResult:
    fecha: date
    precio_diesel: float
    fuente: str


class MemFuelPriceProvider:

    @staticmethod
    def fetch_current_diesel_price() -> MemFuelPriceResult:
        response = httpx.get(
            MEM_URL,
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 TransportesJDA-FuelPriceSync/1.0"
                )
            },
        )
        response.raise_for_status()

        html = response.text

        patterns = [
            r"Q\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*(?:</[^>]+>\s*)*DI[ÉE]SEL",
            r"DI[ÉE]SEL[\s\S]{0,300}?Q\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:
                price = float(match.group(1))

                if 5 <= price <= 100:
                    return MemFuelPriceResult(
                        fecha=date.today(),
                        precio_diesel=price,
                        fuente=MEM_URL,
                    )

        raise RuntimeError(
            "No fue posible identificar el precio del diésel "
            "en la publicación del MEM."
        )