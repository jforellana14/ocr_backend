from datetime import date
from types import SimpleNamespace

import pytest

from app.repositories.financial_repository import FinancialRepository
from app.services.dashboard_service import DashboardService
from app.services.financial_engine import FinancialEngine
from app.services.income_statement_service import IncomeStatementService


def obj(**kwargs):
    return SimpleNamespace(**kwargs)


def test_document_date_iso():
    assert FinancialEngine._document_date("2026-07-15") == date(2026, 7, 15)


def test_document_date_latam():
    assert FinancialEngine._document_date("15/07/2026") == date(2026, 7, 15)


def test_daily_recurring_proration():
    ratio = FinancialEngine._month_overlap_ratio(
        date(2026, 7, 1), date(2026, 7, 15), date(2026, 7, 15)
    )
    assert round(ratio, 6) == round(1 / 31, 6)


def test_monthly_expense_is_prorated_for_partial_month():
    category = obj(activo="SI", afecta_estado_resultados="SI")
    expense = obj(
        activo="SI",
        category=category,
        fecha_inicio=date(2026, 7, 1),
        fecha_fin=None,
        monto=3100,
        periodicidad="MENSUAL",
        meses_prorrateo=1,
    )
    recognized = FinancialEngine._recognized_expense(
        expense, date(2026, 7, 1), date(2026, 7, 10)
    )
    assert recognized == 1000


def test_engine_calculates_dashboard_and_income_statement_from_same_source(monkeypatch):
    settings = obj(costo_combustible_galon=35, porcentaje_isr=25)
    documents = [
        obj(
            fecha="2026-07-10",
            precio_total=10000,
            combustible_consumido=100,
            fuel_price=36,
            bonificacion_piloto=500,
            distancia_viaje=250,
        )
    ]
    admin_category = obj(
        nombre="INTERNET",
        tipo="ADMINISTRATIVO",
        activo="SI",
        afecta_estado_resultados="SI",
    )
    expenses = [
        obj(
            id=1,
            activo="SI",
            category=admin_category,
            descripcion="SERVICIO MENSUAL",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=None,
            periodicidad="MENSUAL",
            meses_prorrateo=1,
            monto=310,
        )
    ]

    monkeypatch.setattr(FinancialRepository, "settings", lambda db: settings)
    monkeypatch.setattr(
        FinancialRepository,
        "documents_for_period",
        lambda db, start, end: documents,
    )
    monkeypatch.setattr(
        FinancialRepository,
        "active_expenses_for_period",
        lambda db, start, end: expenses,
    )

    start, end = date(2026, 7, 1), date(2026, 7, 31)
    dashboard = DashboardService.get_range(None, start, end)
    statement = IncomeStatementService.get_range(None, start, end)

    assert dashboard == statement
    assert dashboard["ingresos"] == 10000
    assert dashboard["costo_combustible"] == 3600
    assert dashboard["costos_directos"] == 4100
    assert dashboard["utilidad_bruta"] == 5900
    assert dashboard["gastos_administrativos"] == 310
    assert dashboard["utilidad_antes_impuestos"] == 5590
    assert dashboard["impuesto_proyectado"] == 1397.5
    assert dashboard["utilidad_neta"] == 4192.5


def test_invalid_range_is_rejected():
    with pytest.raises(ValueError):
        FinancialEngine.get_range(None, date(2026, 7, 2), date(2026, 7, 1))
