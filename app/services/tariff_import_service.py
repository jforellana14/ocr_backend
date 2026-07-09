from datetime import datetime
from sqlalchemy.orm import Session

from models import Route, RatePlan, RatePlanDetail, Document, FuelPrice


FUEL_RANGES = [
    (8.01, 12),
    (12.01, 16),
    (16.01, 20),
    (20.01, 24),
    (24.01, 28),
    (28.01, 32),
    (32.01, 36),
    (36.01, 40),
]


def normalize(value):
    return (value or "").strip().upper()


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def find_fuel_price(db: Session, fecha):
    if not fecha:
        return None

    return (
        db.query(FuelPrice)
        .filter(FuelPrice.fecha <= fecha)
        .order_by(FuelPrice.fecha.desc())
        .first()
    )


def find_price_range(details, fuel_price):
    for detail in details:
        if (
            detail.combustible_min <= fuel_price
            and detail.combustible_max >= fuel_price
        ):
            return detail

    return None


def import_tariff_rows_and_update_documents(
    db: Session,
    rows: list[dict],
    vehicle_type_id: int,
    charge_type_id: int = 1,
    force_recalculate: bool = False
):
    created_routes = 0
    created_plans = 0
    created_details = 0
    updated_documents = 0
    failed_documents = []

    for row in rows:
        origen = normalize(row["origen"])
        destino = normalize(row["destino"])
        kilometraje = row.get("kilometraje")
        consumo = row.get("consumo_diesel")
        prices = row["prices"]

        route = (
            db.query(Route)
            .filter(Route.origen == origen)
            .filter(Route.destino == destino)
            .first()
        )

        if not route:
            route = Route(
                nombre=f"{origen} - {destino}",
                origen=origen,
                destino=destino,
                distancia_km=kilometraje,
                activo="SI"
            )
            db.add(route)
            db.commit()
            db.refresh(route)
            created_routes += 1

        plan_code = f"RUTA-{route.id}-GRANEL-2026"

        plan = (
            db.query(RatePlan)
            .filter(RatePlan.codigo == plan_code)
            .first()
        )

        if not plan:
            plan = RatePlan(
                codigo=plan_code,
                nombre=f"TARIFARIO {route.nombre}",
                scope="GLOBAL",
                client_id=None,
                route_id=route.id,
                vehicle_type_id=vehicle_type_id,
                charge_type_id=charge_type_id,
                producto="GRANEL",
                fecha_inicio=datetime(2026, 1, 1).date(),
                fecha_fin=datetime(2026, 12, 31).date(),
                moneda="GTQ",
                version=1,
                estado="ACTIVO",
                observaciones="Importado desde tarifario granel 2026"
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            created_plans += 1

        existing_details = (
            db.query(RatePlanDetail)
            .filter(RatePlanDetail.rate_plan_id == plan.id)
            .all()
        )

        if not existing_details:
            for index, price in enumerate(prices):
                fuel_min, fuel_max = FUEL_RANGES[index]

                detail = RatePlanDetail(
                    rate_plan_id=plan.id,
                    combustible_min=fuel_min,
                    combustible_max=fuel_max,
                    peso_min=0,
                    peso_max=999999999,
                    precio_unitario=float(price),
                    bonificacion_piloto=0,
                    margen_estimado=None,
                    activo="SI"
                )

                db.add(detail)
                created_details += 1

            db.commit()

        details = (
            db.query(RatePlanDetail)
            .filter(RatePlanDetail.rate_plan_id == plan.id)
            .filter(RatePlanDetail.activo == "SI")
            .all()
        )

        documents_query = (
            db.query(Document)
            .filter(Document.origen == origen)
            .filter(Document.destino == destino)
        )

        if not force_recalculate:
            documents_query = documents_query.filter(Document.precio_total == None)

        documents = documents_query.all()

        for doc in documents:
            fecha_doc = parse_date(doc.fecha)
            fuel = find_fuel_price(db, fecha_doc)

            if not fuel:
                failed_documents.append({
                    "document_id": doc.id,
                    "motivo": "No existe precio de combustible para la fecha."
                })
                continue

            detail = find_price_range(details, fuel.precio_galon)

            if not detail:
                failed_documents.append({
                    "document_id": doc.id,
                    "motivo": f"No existe rango para combustible {fuel.precio_galon}."
                })
                continue

            try:
                quintales = float(doc.peso_entregado)
            except Exception:
                failed_documents.append({
                    "document_id": doc.id,
                    "motivo": "Peso entregado inválido."
                })
                continue

            doc.route_id = route.id
            doc.fuel_price_id = fuel.id
            doc.fuel_price = fuel.precio_galon
            doc.rate_plan_id = plan.id
            doc.rate_plan_detail_id = detail.id
            doc.precio_unitario = detail.precio_unitario
            doc.precio_total = quintales * detail.precio_unitario
            doc.bonificacion_piloto = detail.bonificacion_piloto or 0
            doc.pricing_version = 1

            updated_documents += 1

        db.commit()

    return {
        "created_routes": created_routes,
        "created_plans": created_plans,
        "created_details": created_details,
        "updated_documents": updated_documents,
        "failed_documents": failed_documents
    }