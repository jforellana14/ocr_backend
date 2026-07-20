from datetime import date
from types import SimpleNamespace

from app.repositories.financial_repository import FinancialRepository
from app.repositories.profitability_repository import ProfitabilityRepository
from app.services.financial_engine import FinancialEngine
from app.services.profitability_service import ProfitabilityService


def obj(**kwargs):
    return SimpleNamespace(**kwargs)


def test_profitability_reconciles_with_financial_engine(monkeypatch):
    documents = [
        obj(
            fecha="2026-07-10",
            cliente_id=1,
            cliente=obj(nombre="CLIENTE A"),
            truck_id=1,
            camion=obj(codigo="T-01", placa="P001AAA"),
            route_id=1,
            ruta=obj(nombre="RUTA A"),
            piloto="PILOTO A",
            producto="MAIZ",
            precio_total=10000,
            combustible_consumido=100,
            fuel_price=35,
            bonificacion_piloto=500,
            distancia_viaje=250,
        ),
        obj(
            fecha="2026-07-11",
            cliente_id=2,
            cliente=obj(nombre="CLIENTE B"),
            truck_id=2,
            camion=obj(codigo="T-02", placa="P002AAA"),
            route_id=2,
            ruta=obj(nombre="RUTA B"),
            piloto="PILOTO B",
            producto="TRIGO",
            precio_total=5000,
            combustible_consumido=50,
            fuel_price=35,
            bonificacion_piloto=250,
            distancia_viaje=100,
        ),
    ]
    monkeypatch.setattr(
        ProfitabilityRepository,
        "documents_for_period",
        lambda db, start, end: documents,
    )
    monkeypatch.setattr(
        FinancialEngine,
        "get_range",
        lambda db, start, end: {"utilidad_neta": 7000},
    )

    result = ProfitabilityService.by_client(
        None, date(2026, 7, 1), date(2026, 7, 31)
    )

    assert result["totals"]["income"] == 15000
    assert result["totals"]["enterprise_profit"] == 7000
    assert result["totals"]["reconciliation_difference"] == 0
    assert len(result["items"]) == 2


def test_zero_income_expenses_are_distributed_by_trip_count(monkeypatch):
    documents = [
        obj(
            fecha="2026-07-10",
            cliente_id=1,
            cliente=obj(nombre="CLIENTE A"),
            precio_total=0,
            combustible_consumido=10,
            fuel_price=10,
            bonificacion_piloto=0,
            distancia_viaje=10,
        ),
        obj(
            fecha="2026-07-11",
            cliente_id=2,
            cliente=obj(nombre="CLIENTE B"),
            precio_total=0,
            combustible_consumido=10,
            fuel_price=10,
            bonificacion_piloto=0,
            distancia_viaje=10,
        ),
    ]
    monkeypatch.setattr(
        ProfitabilityRepository,
        "documents_for_period",
        lambda db, start, end: documents,
    )
    monkeypatch.setattr(
        FinancialEngine,
        "get_range",
        lambda db, start, end: {"utilidad_neta": -400},
    )

    result = ProfitabilityService.by_client(
        None, date(2026, 7, 1), date(2026, 7, 31)
    )

    allocations = [item["allocated_general_expenses"] for item in result["items"]]
    assert allocations == [100, 100]
    assert result["totals"]["enterprise_profit"] == -400
    assert result["totals"]["reconciliation_difference"] == 0
