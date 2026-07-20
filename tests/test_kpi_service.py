from app.services.kpi_service import KPIService


def test_kpis_are_calculated_from_financial_engine_result():
    result = {
        "fecha_inicio": "2026-07-01",
        "fecha_fin": "2026-07-31",
        "ingresos": 10000,
        "viajes": 4,
        "distancia_km": 1000,
        "combustible_galones": 100,
        "costo_combustible": 3500,
        "costos_directos": 5000,
        "gastos_operativos": 500,
        "gastos_administrativos": 1000,
        "utilidad_bruta": 5000,
        "utilidad_operativa": 3500,
        "utilidad_neta": 2625,
        "impuesto_proyectado": 875,
    }

    kpis = KPIService.from_financial_result(result)

    assert kpis["margenes"]["margen_bruto"] == 50
    assert kpis["margenes"]["margen_operativo"] == 35
    assert kpis["margenes"]["margen_neto"] == 26.25
    assert kpis["estructura_costos"]["costos_directos_sobre_ingresos"] == 50
    assert kpis["estructura_costos"]["combustible_sobre_ingresos"] == 35
    assert kpis["eficiencia"]["ingreso_promedio_por_viaje"] == 2500
    assert kpis["eficiencia"]["utilidad_neta_promedio_por_viaje"] == 656.25
    assert kpis["eficiencia"]["ingreso_por_km"] == 10
    assert kpis["eficiencia"]["costo_directo_por_km"] == 5
    assert kpis["eficiencia"]["km_por_galon"] == 10
    assert kpis["eficiencia"]["costo_combustible_por_galon"] == 35


def test_kpis_handle_empty_period_without_division_errors():
    kpis = KPIService.from_financial_result(
        {
            "ingresos": 0,
            "viajes": 0,
            "distancia_km": 0,
            "combustible_galones": 0,
        }
    )

    assert kpis["margenes"]["margen_bruto"] == 0
    assert kpis["margenes"]["margen_operativo"] == 0
    assert kpis["margenes"]["margen_neto"] == 0
    assert kpis["eficiencia"]["ingreso_promedio_por_viaje"] == 0
    assert kpis["eficiencia"]["km_por_galon"] == 0
