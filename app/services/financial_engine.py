from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.financial_repository import FinancialRepository


class FinancialEngine:
    """Fuente única de verdad para Dashboard y Estado de Resultados."""

    FREQUENCIES = {
        "MENSUAL": 1, "BIMESTRAL": 2, "TRIMESTRAL": 3,
        "SEMESTRAL": 6, "ANUAL": 12,
    }
    BUCKETS = {
        "COSTO_DIRECTO": "otros_costos_directos",
        "DIRECTO": "otros_costos_directos",
        "OPERATIVO": "gastos_operativos",
        "GASTO_OPERATIVO": "gastos_operativos",
        "MANTENIMIENTO": "gastos_operativos",
        "ADMINISTRATIVO": "gastos_administrativos",
        "GASTO_ADMINISTRATIVO": "gastos_administrativos",
        "FIJO": "gastos_administrativos",
        "GASTO_FIJO": "gastos_administrativos",
        "FINANCIERO": "gastos_financieros",
        "GASTO_FINANCIERO": "gastos_financieros",
        "IMPUESTO": "impuestos_registrados",
        "IMPUESTOS": "impuestos_registrados",
        "OTRO": "otros_gastos", "OTROS": "otros_gastos",
    }

    @staticmethod
    def _money(value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize(value, default="") -> str:
        return str(value or default).strip().upper()

    @staticmethod
    def _document_date(value) -> Optional[date]:
        if isinstance(value, datetime): return value.date()
        if isinstance(value, date): return value
        raw = str(value or "").strip()[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y"):
            try: return datetime.strptime(raw, fmt).date()
            except ValueError: pass
        return None

    @staticmethod
    def _month_start(value: date) -> date:
        return date(value.year, value.month, 1)

    @staticmethod
    def _month_end(value: date) -> date:
        return date(value.year, value.month, monthrange(value.year, value.month)[1])

    @staticmethod
    def _add_months(value: date, months: int) -> date:
        idx = value.year * 12 + value.month - 1 + months
        return date(idx // 12, idx % 12 + 1, 1)

    @classmethod
    def _month_overlap_ratio(cls, month: date, start: date, end: date) -> float:
        month_end = cls._month_end(month)
        overlap_start, overlap_end = max(month, start), min(month_end, end)
        if overlap_end < overlap_start: return 0.0
        return ((overlap_end - overlap_start).days + 1) / month_end.day

    @classmethod
    def _recognized_expense(cls, expense, start: date, end: date) -> float:
        category = getattr(expense, "category", None)
        if cls._normalize(getattr(expense, "activo", "SI"), "SI") != "SI": return 0.0
        if category and cls._normalize(getattr(category, "activo", "SI"), "SI") != "SI": return 0.0
        if category and cls._normalize(getattr(category, "afecta_estado_resultados", "SI"), "SI") != "SI": return 0.0
        exp_start = expense.fecha_inicio
        exp_end = expense.fecha_fin
        if not exp_start or exp_start > end or (exp_end and exp_end < start): return 0.0
        amount = cls._money(expense.monto)
        frequency = cls._normalize(expense.periodicidad, "UNICO")
        spread = max(int(getattr(expense, "meses_prorrateo", 1) or 1), 1)

        # Gasto único: fecha completa o prorrateo contable mensual cuando se configuró.
        if frequency in {"UNICO", "UNICA"} and spread == 1:
            return amount if start <= exp_start <= end else 0.0
        if frequency in {"UNICO", "UNICA"}:
            total = 0.0
            first = cls._month_start(exp_start)
            for offset in range(spread):
                month = cls._add_months(first, offset)
                if exp_end and month > cls._month_start(exp_end): break
                total += (amount / spread) * cls._month_overlap_ratio(month, start, end)
            return total

        interval = cls.FREQUENCIES.get(frequency)
        if not interval: return 0.0
        total, month = 0.0, cls._month_start(exp_start)
        while month <= cls._month_start(end):
            if (not exp_end or month <= cls._month_start(exp_end)):
                total += amount * cls._month_overlap_ratio(month, start, end)
            month = cls._add_months(month, interval)
        return total

    @classmethod
    def get_range(cls, db: Session, start: date, end: date) -> dict:
        if end < start: raise ValueError("La fecha final no puede ser menor que la inicial.")
        settings = FinancialRepository.settings(db)
        docs = [d for d in FinancialRepository.documents_for_period(db, start, end) if (dt := cls._document_date(d.fecha)) and start <= dt <= end]
        ingresos = sum(cls._money(d.precio_total) for d in docs)
        combustible_galones = sum(cls._money(d.combustible_consumido) for d in docs)
        costo_combustible = sum(cls._money(d.combustible_consumido) * cls._money(d.fuel_price or settings.costo_combustible_galon) for d in docs)
        bonificaciones = sum(cls._money(d.bonificacion_piloto) for d in docs)
        buckets = {k: 0.0 for k in ("otros_costos_directos", "gastos_operativos", "gastos_administrativos", "gastos_financieros", "impuestos_registrados", "otros_gastos")}
        detalle_gastos = []
        for expense in FinancialRepository.active_expenses_for_period(db, start, end):
            recognized = cls._recognized_expense(expense, start, end)
            if not recognized: continue
            category = getattr(expense, "category", None)
            kind = cls._normalize(getattr(category, "tipo", None), "OTRO")
            bucket = cls.BUCKETS.get(kind, "otros_gastos")
            buckets[bucket] += recognized
            detalle_gastos.append({"id": expense.id, "categoria": getattr(category, "nombre", "SIN CATEGORÍA"), "tipo": kind, "descripcion": expense.descripcion, "monto_reconocido": round(recognized, 2)})

        costos_directos = costo_combustible + bonificaciones + buckets["otros_costos_directos"]
        utilidad_bruta = ingresos - costos_directos
        gastos_operacion = buckets["gastos_operativos"]
        utilidad_operativa = utilidad_bruta - gastos_operacion - buckets["gastos_administrativos"]
        utilidad_antes_impuestos = utilidad_operativa - buckets["gastos_financieros"] - buckets["otros_gastos"] - buckets["impuestos_registrados"]
        tasa_isr = max(cls._money(settings.porcentaje_isr), 0.0)
        impuesto_proyectado = max(utilidad_antes_impuestos, 0.0) * tasa_isr / 100
        utilidad_neta = utilidad_antes_impuestos - impuesto_proyectado
        gastos_sin_impuesto_proyectado = costos_directos + gastos_operacion + buckets["gastos_administrativos"] + buckets["gastos_financieros"] + buckets["otros_gastos"] + buckets["impuestos_registrados"]
        gastos_totales = gastos_sin_impuesto_proyectado + impuesto_proyectado
        margen_bruto = utilidad_bruta / ingresos * 100 if ingresos else 0.0
        margen_neto = utilidad_neta / ingresos * 100 if ingresos else 0.0

        money = lambda x: round(x, 2)
        return {
            "fecha_inicio": start.isoformat(), "fecha_fin": end.isoformat(),
            "ingresos": money(ingresos), "viajes": len(docs),
            "combustible_galones": money(combustible_galones), "costo_combustible": money(costo_combustible),
            "bonificaciones": money(bonificaciones), "otros_costos_directos": money(buckets["otros_costos_directos"]),
            "costos_directos": money(costos_directos), "utilidad_bruta": money(utilidad_bruta), "margen_bruto": money(margen_bruto),
            "gastos_operativos": money(gastos_operacion), "gastos_administrativos": money(buckets["gastos_administrativos"]),
            "gastos_financieros": money(buckets["gastos_financieros"]), "otros_gastos": money(buckets["otros_gastos"]),
            "impuestos_registrados": money(buckets["impuestos_registrados"]), "porcentaje_isr": money(tasa_isr),
            "impuesto_proyectado": money(impuesto_proyectado), "impuestos": money(buckets["impuestos_registrados"] + impuesto_proyectado),
            "utilidad_operativa": money(utilidad_operativa), "utilidad_antes_impuestos": money(utilidad_antes_impuestos),
            "utilidad_neta": money(utilidad_neta), "utilidad": money(utilidad_neta), "margen_neto": money(margen_neto),
            "gastos_registrados": money(gastos_sin_impuesto_proyectado), "gastos_totales": money(gastos_totales), "gastos": money(gastos_totales),
            "distancia_km": money(sum(cls._money(d.distancia_viaje) for d in docs)),
            "detalle_gastos": detalle_gastos,
            "estado_resultados": [
                {"cuenta": "INGRESOS POR SERVICIOS", "monto": money(ingresos), "nivel": 0},
                {"cuenta": "(-) COMBUSTIBLE", "monto": money(costo_combustible), "nivel": 1},
                {"cuenta": "(-) BONIFICACIONES A PILOTOS", "monto": money(bonificaciones), "nivel": 1},
                {"cuenta": "(-) OTROS COSTOS DIRECTOS", "monto": money(buckets["otros_costos_directos"]), "nivel": 1},
                {"cuenta": "UTILIDAD BRUTA", "monto": money(utilidad_bruta), "nivel": 0, "subtotal": True},
                {"cuenta": "(-) GASTOS OPERATIVOS", "monto": money(gastos_operacion), "nivel": 1},
                {"cuenta": "(-) GASTOS ADMINISTRATIVOS Y FIJOS", "monto": money(buckets["gastos_administrativos"]), "nivel": 1},
                {"cuenta": "UTILIDAD OPERATIVA", "monto": money(utilidad_operativa), "nivel": 0, "subtotal": True},
                {"cuenta": "(-) GASTOS FINANCIEROS", "monto": money(buckets["gastos_financieros"]), "nivel": 1},
                {"cuenta": "(-) OTROS GASTOS E IMPUESTOS REGISTRADOS", "monto": money(buckets["otros_gastos"] + buckets["impuestos_registrados"]), "nivel": 1},
                {"cuenta": "UTILIDAD ANTES DE ISR", "monto": money(utilidad_antes_impuestos), "nivel": 0, "subtotal": True},
                {"cuenta": f"(-) ISR PROYECTADO ({tasa_isr:.2f}%)", "monto": money(impuesto_proyectado), "nivel": 1},
                {"cuenta": "UTILIDAD NETA PROYECTADA", "monto": money(utilidad_neta), "nivel": 0, "subtotal": True},
            ],
        }

    @classmethod
    def get_month(cls, db: Session, year: int, month: int) -> dict:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        result = cls.get_range(db, start, end)
        result["periodo"] = f"{year}-{month:02d}"
        return result
