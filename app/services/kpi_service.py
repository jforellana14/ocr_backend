from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.services.financial_engine import FinancialEngine


class KPIService:
    """Construye indicadores gerenciales a partir del FinancialEngine.

    No consulta modelos ni recalcula importes financieros. De esta forma los
    indicadores siempre coinciden con Dashboard y Estado de Resultados.
    """

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _percentage(cls, numerator: Any, denominator: Any) -> float:
        base = cls._number(denominator)
        if base == 0:
            return 0.0
        return round(cls._number(numerator) / base * 100, 2)

    @classmethod
    def from_financial_result(cls, result: dict[str, Any]) -> dict[str, Any]:
        """Convierte el resultado canónico del motor en KPIs ejecutivos."""

        ingresos = cls._number(result.get("ingresos"))
        viajes = int(cls._number(result.get("viajes")))
        distancia_km = cls._number(result.get("distancia_km"))
        combustible_galones = cls._number(result.get("combustible_galones"))
        costos_directos = cls._number(result.get("costos_directos"))
        gastos_operativos = cls._number(result.get("gastos_operativos"))
        gastos_administrativos = cls._number(result.get("gastos_administrativos"))
        utilidad_bruta = cls._number(result.get("utilidad_bruta"))
        utilidad_operativa = cls._number(result.get("utilidad_operativa"))
        utilidad_neta = cls._number(result.get("utilidad_neta"))
        impuesto_proyectado = cls._number(result.get("impuesto_proyectado"))
        costo_combustible = cls._number(result.get("costo_combustible"))

        ingreso_promedio_viaje = ingresos / viajes if viajes else 0.0
        utilidad_neta_promedio_viaje = utilidad_neta / viajes if viajes else 0.0
        ingreso_por_km = ingresos / distancia_km if distancia_km else 0.0
        costo_directo_por_km = costos_directos / distancia_km if distancia_km else 0.0
        km_por_galon = distancia_km / combustible_galones if combustible_galones else 0.0
        costo_combustible_por_galon = (
            costo_combustible / combustible_galones if combustible_galones else 0.0
        )

        return {
            "fecha_inicio": result.get("fecha_inicio"),
            "fecha_fin": result.get("fecha_fin"),
            "periodo": result.get("periodo"),
            "moneda": "GTQ",
            "resumen": {
                "ingresos": round(ingresos, 2),
                "utilidad_bruta": round(utilidad_bruta, 2),
                "utilidad_operativa": round(utilidad_operativa, 2),
                "utilidad_neta": round(utilidad_neta, 2),
                "impuesto_proyectado": round(impuesto_proyectado, 2),
                "viajes": viajes,
                "distancia_km": round(distancia_km, 2),
            },
            "margenes": {
                "margen_bruto": cls._percentage(utilidad_bruta, ingresos),
                "margen_operativo": cls._percentage(utilidad_operativa, ingresos),
                "margen_neto": cls._percentage(utilidad_neta, ingresos),
            },
            "estructura_costos": {
                "costos_directos_sobre_ingresos": cls._percentage(
                    costos_directos, ingresos
                ),
                "combustible_sobre_ingresos": cls._percentage(
                    costo_combustible, ingresos
                ),
                "gastos_operativos_sobre_ingresos": cls._percentage(
                    gastos_operativos, ingresos
                ),
                "gastos_administrativos_sobre_ingresos": cls._percentage(
                    gastos_administrativos, ingresos
                ),
                "isr_proyectado_sobre_ingresos": cls._percentage(
                    impuesto_proyectado, ingresos
                ),
            },
            "eficiencia": {
                "ingreso_promedio_por_viaje": round(ingreso_promedio_viaje, 2),
                "utilidad_neta_promedio_por_viaje": round(
                    utilidad_neta_promedio_viaje, 2
                ),
                "ingreso_por_km": round(ingreso_por_km, 2),
                "costo_directo_por_km": round(costo_directo_por_km, 2),
                "km_por_galon": round(km_por_galon, 2),
                "costo_combustible_por_galon": round(
                    costo_combustible_por_galon, 2
                ),
            },
        }

    @classmethod
    def get_range(cls, db: Session, start: date, end: date) -> dict[str, Any]:
        result = FinancialEngine.get_range(db, start, end)
        return cls.from_financial_result(result)

    @classmethod
    def get_month(cls, db: Session, year: int, month: int) -> dict[str, Any]:
        result = FinancialEngine.get_month(db, year, month)
        return cls.from_financial_result(result)
