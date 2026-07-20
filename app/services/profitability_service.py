from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.repositories.profitability_repository import ProfitabilityRepository
from app.services.financial_engine import FinancialEngine


class ProfitabilityService:
    """Calcula rentabilidad operativa y empresarial por dimensión.

    La rentabilidad operativa considera únicamente los costos directamente
    identificables en cada viaje: combustible y bonificación del piloto.

    La rentabilidad empresarial distribuye proporcionalmente por ingresos la
    diferencia entre la utilidad operativa directa de los viajes y la utilidad
    neta calculada por ``FinancialEngine``. De esta forma se incorporan otros
    costos directos, gastos operativos, administrativos, financieros, otros
    gastos, impuestos registrados e ISR proyectado, y el total del reporte
    siempre coincide con el Estado de Resultados.
    """

    DIMENSIONS = {"client", "driver", "truck", "route", "product"}

    @staticmethod
    def _money(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _text(value: Any, default: str = "SIN ASIGNAR") -> str:
        text = str(value or "").strip()
        return text if text else default

    @classmethod
    def _dimension_value(cls, document: Any, dimension: str) -> tuple[str, str]:
        if dimension == "client":
            related = getattr(document, "cliente", None)
            raw_id = getattr(document, "cliente_id", None)
            name = getattr(related, "nombre", None)
            return cls._text(raw_id, "SIN_ID"), cls._text(name, "SIN CLIENTE")

        if dimension == "driver":
            name = cls._text(getattr(document, "piloto", None), "SIN PILOTO")
            return name.upper(), name

        if dimension == "truck":
            related = getattr(document, "camion", None)
            raw_id = getattr(document, "truck_id", None)
            label = (
                getattr(related, "codigo", None)
                or getattr(related, "placa", None)
                or (f"CAMIÓN {raw_id}" if raw_id is not None else None)
            )
            return cls._text(raw_id, "SIN_ID"), cls._text(label, "SIN CAMIÓN")

        if dimension == "route":
            related = getattr(document, "ruta", None)
            raw_id = getattr(document, "route_id", None)
            label = getattr(related, "nombre", None)
            if not label:
                origin = cls._text(getattr(document, "origen", None), "")
                destination = cls._text(getattr(document, "destino", None), "")
                label = f"{origin} - {destination}".strip(" -") or None
            return cls._text(raw_id, "SIN_ID"), cls._text(label, "SIN RUTA")

        if dimension == "product":
            name = cls._text(getattr(document, "producto", None), "SIN PRODUCTO")
            return name.upper(), name

        raise ValueError(f"Dimensión de rentabilidad no soportada: {dimension}")

    @classmethod
    def get_by_dimension(
        cls,
        db: Session,
        start: date,
        end: date,
        dimension: str,
    ) -> dict[str, Any]:
        if end < start:
            raise ValueError("La fecha final no puede ser menor que la inicial.")

        dimension = str(dimension or "").strip().lower()
        if dimension not in cls.DIMENSIONS:
            allowed = ", ".join(sorted(cls.DIMENSIONS))
            raise ValueError(f"Dimensión inválida. Valores permitidos: {allowed}.")

        financial = FinancialEngine.get_range(db, start, end)

        documents = [
            document
            for document in ProfitabilityRepository.documents_for_period(db, start, end)
            if (
                (document_date := FinancialEngine._document_date(document.fecha))
                and start <= document_date <= end
            )
        ]

        # El costo de combustible debe coincidir con FinancialEngine. Cuando el
        # documento no tiene precio propio, usamos la configuración financiera.
        financial_settings = None
        if any(not cls._money(getattr(doc, "fuel_price", None)) for doc in documents):
            from app.repositories.financial_repository import FinancialRepository

            financial_settings = FinancialRepository.settings(db)

        groups: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: {
                "income": 0.0,
                "fuel_cost": 0.0,
                "driver_bonus": 0.0,
                "distance_km": 0.0,
                "fuel_gallons": 0.0,
                "trips": 0.0,
            }
        )

        for document in documents:
            key = cls._dimension_value(document, dimension)
            bucket = groups[key]
            income = cls._money(getattr(document, "precio_total", None))
            gallons = cls._money(getattr(document, "combustible_consumido", None))
            configured_price = cls._money(
                getattr(financial_settings, "costo_combustible_galon", None)
            )
            fuel_price = cls._money(getattr(document, "fuel_price", None)) or configured_price

            bucket["income"] += income
            bucket["fuel_gallons"] += gallons
            bucket["fuel_cost"] += gallons * fuel_price
            bucket["driver_bonus"] += cls._money(
                getattr(document, "bonificacion_piloto", None)
            )
            bucket["distance_km"] += cls._money(
                getattr(document, "distancia_viaje", None)
            )
            bucket["trips"] += 1

        total_income = sum(group["income"] for group in groups.values())
        total_trips = sum(group["trips"] for group in groups.values())
        total_operating_profit = sum(
            group["income"] - group["fuel_cost"] - group["driver_bonus"]
            for group in groups.values()
        )
        target_net_profit = cls._money(financial.get("utilidad_neta"))
        total_allocable_expenses = total_operating_profit - target_net_profit

        items: list[dict[str, Any]] = []
        allocated_running_total = 0.0
        ordered_groups = sorted(
            groups.items(),
            key=lambda pair: pair[1]["income"],
            reverse=True,
        )

        for index, ((dimension_id, name), values) in enumerate(ordered_groups):
            income = values["income"]
            operating_cost = values["fuel_cost"] + values["driver_bonus"]
            operating_profit = income - operating_cost
            # La distribución principal es por participación de ingresos. Si el
            # período no tiene ingresos, se distribuye por cantidad de viajes
            # para evitar cargar todo el gasto al último grupo.
            share = (
                income / total_income
                if total_income
                else (values["trips"] / total_trips if total_trips else 0.0)
            )

            # En el último registro absorbemos cualquier diferencia mínima de
            # punto flotante para que el total cuadre exactamente con el motor.
            if index == len(ordered_groups) - 1:
                allocated_expenses = total_allocable_expenses - allocated_running_total
            else:
                allocated_expenses = total_allocable_expenses * share
                allocated_running_total += allocated_expenses

            enterprise_profit = operating_profit - allocated_expenses
            operating_margin = operating_profit / income * 100 if income else 0.0
            enterprise_margin = enterprise_profit / income * 100 if income else 0.0

            items.append(
                {
                    "id": dimension_id,
                    "name": name,
                    "trips": int(values["trips"]),
                    "income": round(income, 2),
                    "fuel_gallons": round(values["fuel_gallons"], 2),
                    "fuel_cost": round(values["fuel_cost"], 2),
                    "driver_bonus": round(values["driver_bonus"], 2),
                    "direct_operating_cost": round(operating_cost, 2),
                    "operating_profit": round(operating_profit, 2),
                    "operating_margin": round(operating_margin, 2),
                    "income_share": round(share * 100, 2),
                    "allocated_general_expenses": round(allocated_expenses, 2),
                    "enterprise_profit": round(enterprise_profit, 2),
                    "enterprise_margin": round(enterprise_margin, 2),
                    "distance_km": round(values["distance_km"], 2),
                }
            )

        items.sort(key=lambda item: item["enterprise_profit"], reverse=True)

        return {
            "dimension": dimension,
            "period": {"from": start.isoformat(), "to": end.isoformat()},
            "items": items,
            "totals": {
                "trips": len(documents),
                "income": round(total_income, 2),
                "fuel_cost": round(sum(v["fuel_cost"] for v in groups.values()), 2),
                "driver_bonus": round(
                    sum(v["driver_bonus"] for v in groups.values()), 2
                ),
                "operating_profit": round(total_operating_profit, 2),
                "allocated_general_expenses": round(total_allocable_expenses, 2),
                "enterprise_profit": round(target_net_profit, 2),
                "financial_engine_net_profit": round(target_net_profit, 2),
                "reconciliation_difference": round(
                    sum(item["enterprise_profit"] for item in items)
                    - target_net_profit,
                    2,
                ),
            },
        }

    @classmethod
    def by_client(cls, db: Session, start: date, end: date) -> dict[str, Any]:
        return cls.get_by_dimension(db, start, end, "client")

    @classmethod
    def by_driver(cls, db: Session, start: date, end: date) -> dict[str, Any]:
        return cls.get_by_dimension(db, start, end, "driver")

    @classmethod
    def by_truck(cls, db: Session, start: date, end: date) -> dict[str, Any]:
        return cls.get_by_dimension(db, start, end, "truck")

    @classmethod
    def by_route(cls, db: Session, start: date, end: date) -> dict[str, Any]:
        return cls.get_by_dimension(db, start, end, "route")

    @classmethod
    def by_product(cls, db: Session, start: date, end: date) -> dict[str, Any]:
        return cls.get_by_dimension(db, start, end, "product")
