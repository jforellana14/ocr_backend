from dataclasses import dataclass
from typing import Optional


@dataclass
class PricingResult:

    fuel_price_id: int

    fuel_price: float

    rate_plan_id: int

    rate_plan_detail_id: int

    precio_unitario: float

    peso: float

    precio_total: float

    bonificacion: float

    margen: Optional[float] = None

    version: int = 1