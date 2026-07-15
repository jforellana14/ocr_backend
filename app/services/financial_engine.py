from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session, joinedload

from models import Document, Expense


@dataclass(frozen=True)
class Period:
    start: date
    end: date


class FinancialEngine:
    """Fuente única de verdad para los resultados financieros del ERP."""

    FREQUENCY_INTERVALS = {
        "MENSUAL": 1,
        "BIMESTRAL": 2,
        "TRIMESTRAL": 3,
        "SEMESTRAL": 6,
        "ANUAL": 12,
    }

    CATEGORY_BUCKETS = {
        "OPERATIVO": "costos_directos",
        "COSTO_DIRECTO": "costos_directos",
        "DIRECTO": "costos_directos",
        "MANTENIMIENTO": "gastos_operativos",
        "GASTO_OPERATIVO": "gastos_operativos",
        "ADMINISTRATIVO": "gastos_administrativos",
        "GASTO_ADMINISTRATIVO": "gastos_administrativos",
        "FINANCIERO": "gastos_financieros",
        "GASTO_FINANCIERO": "gastos_financieros",
        "IMPUESTO": "impuestos",
        "IMPUESTOS": "impuestos",
        "OTRO": "otros_gastos",
        "OTROS": "otros_gastos",
    }

    @staticmethod
    def _normalize(value: object, default: str = "") -> str:
        return str(value or default).strip().upper()

    @staticmethod
    def _parse_document_date(value: object) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        raw = str(value).strip()
        if not raw:
            return None

        for fmt in (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d/%m/%y",
        ):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _month_start(value: date) -> date:
        return date(value.year, value.month, 1)

    @staticmethod
    def _month_end(value: date) -> date:
        return date(value.year, value.month, monthrange(value.year, value.month)[1])

    @staticmethod
    def _add_months(value: date, months: int) -> date:
        index = value.year * 12 + value.month - 1 + months
        return date(index // 12, index % 12 + 1, 1)

    @classmethod
    def _iter_months(cls, start: date, end: date) -> Iterable[Period]:
        current = cls._month_start(start)
        last = cls._month_start(end)
        while current <= last:
            yield Period(current, cls._month_end(current))
            current = cls._add_months(current, 1)

    @classmethod
    def _expense_applies_to_month(
        cls,
        expense: Expense,
        period: Period,
    ) -> bool:
        if cls._normalize(expense.activo, "SI") != "SI":
            return False

        category = getattr(expense, "category", None)
        if category is not None:
            if cls._normalize(category.activo, "SI") != "SI":
                return False
            if cls._normalize(category.afecta_estado_resultados, "SI") != "SI":
                return False

        start = expense.fecha_inicio
        end = expense.fecha_fin
        frequency = cls._normalize(expense.periodicidad, "UNICO")

        if not start:
            return False

        if frequency in {"UNICO", "UNICA"}:
            return period.start <= start <= period.end

        if start > period.end:
            return False
        if end and end < period.start:
            return False

        month_difference = (
            (period.start.year - start.year) * 12
            + period.start.month
            - start.month
        )
        if month_difference < 0:
            return False

        interval = cls.FREQUENCY_INTERVALS.get(frequency)
        return bool(interval) and month_difference % interval == 0

    @classmethod
    def _expense_bucket(cls, expense: Expense) -> str:
        category = getattr(expense, "category", None)
        category_type = cls._normalize(
            getattr(category, "tipo", None),
            "OTRO",
        )
        return cls.CATEGORY_BUCKETS.get(category_type, "otros_gastos")

    @classmethod
    def get_range(cls, db: Session, start: date, end: date) -> dict:
        if end < start:
            raise ValueError("La fecha final no puede ser menor que la fecha inicial.")

        documents = db.query(Document).all()
        period_documents = []

        for document in documents:
            document_date = cls._parse_document_date(document.fecha)
            if document_date and start <= document_date <= end:
                period_documents.append(document)

        ingresos = sum(float(item.precio_total or 0) for item in period_documents)
        bonificaciones = sum(
            float(item.bonificacion_piloto or 0)
            for item in period_documents
        )

        expenses = (
            db.query(Expense)
            .options(joinedload(Expense.category))
            .filter(Expense.activo == "SI")
            .all()
        )

        buckets = {
            "costos_directos": 0.0,
            "gastos_operativos": 0.0,
            "gastos_administrativos": 0.0,
            "gastos_financieros": 0.0,
            "impuestos": 0.0,
            "otros_gastos": 0.0,
        }
        expense_occurrences = 0

        for month in cls._iter_months(start, end):
            for expense in expenses:
                if not cls._expense_applies_to_month(expense, month):
                    continue
                bucket = cls._expense_bucket(expense)
                buckets[bucket] += float(expense.monto or 0)
                expense_occurrences += 1

        # Las bonificaciones son costo directo, pero se presentan por separado.
        costos_directos_gastos = buckets["costos_directos"]
        costos_directos_totales = costos_directos_gastos + bonificaciones

        utilidad_bruta = ingresos - costos_directos_totales
        utilidad_operativa = utilidad_bruta - buckets["gastos_operativos"]
        utilidad_antes_impuestos = (
            utilidad_operativa
            - buckets["gastos_administrativos"]
            - buckets["gastos_financieros"]
            - buckets["otros_gastos"]
        )
        utilidad_neta = utilidad_antes_impuestos - buckets["impuestos"]

        gastos_registrados = sum(buckets.values())
        gastos_totales = gastos_registrados + bonificaciones
        margen_neto = (utilidad_neta / ingresos * 100) if ingresos else 0.0

        return {
            "fecha_inicio": start.isoformat(),
            "fecha_fin": end.isoformat(),
            "ingresos": round(ingresos, 2),
            "bonificaciones": round(bonificaciones, 2),
            "costos_directos_gastos": round(costos_directos_gastos, 2),
            "costos_directos": round(costos_directos_totales, 2),
            "gastos_operativos": round(buckets["gastos_operativos"], 2),
            "gastos_administrativos": round(
                buckets["gastos_administrativos"], 2
            ),
            "gastos_financieros": round(buckets["gastos_financieros"], 2),
            "impuestos": round(buckets["impuestos"], 2),
            "otros_gastos": round(buckets["otros_gastos"], 2),
            "gastos_registrados": round(gastos_registrados, 2),
            "gastos_totales": round(gastos_totales, 2),
            # Compatibilidad con frontend previo.
            "gastos": round(gastos_registrados, 2),
            "utilidad_bruta": round(utilidad_bruta, 2),
            "utilidad_operativa": round(utilidad_operativa, 2),
            "utilidad_antes_impuestos": round(utilidad_antes_impuestos, 2),
            "utilidad_neta": round(utilidad_neta, 2),
            "utilidad": round(utilidad_neta, 2),
            "margen_neto": round(margen_neto, 2),
            "viajes": len(period_documents),
            "combustible_galones": round(
                sum(float(item.combustible_consumido or 0) for item in period_documents),
                2,
            ),
            "distancia_km": round(
                sum(float(item.distancia_viaje or 0) for item in period_documents),
                2,
            ),
            "gastos_activos": len(expenses),
            "ocurrencias_gastos": expense_occurrences,
        }

    @classmethod
    def get_month(cls, db: Session, year: int, month: int) -> dict:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        result = cls.get_range(db, start, end)
        result["periodo"] = f"{year}-{month:02d}"
        return result
