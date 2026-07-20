import re
import unicodedata
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    ChargeType,
    Document,
    FuelPrice,
    RatePlan,
    RatePlanDetail,
    Route,
    VehicleType,
)


FUEL_RANGES = [
    (8.01, 12.00),
    (12.01, 16.00),
    (16.01, 20.00),
    (20.01, 24.00),
    (24.01, 28.00),
    (28.01, 32.00),
    (32.01, 36.00),
    (36.01, 40.00),
]


def normalize(value: Optional[str]) -> str:
    """
    Normalización para comparar rutas antiguas con rutas importadas.

    Ejemplos:
    'Puerto Quetzal - Zacapa'
    'PUERTO QUETZAL, ZACAPA'
    terminan con una representación comparable.
    """
    text = str(value or "").strip().upper()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_date(value) -> Optional[datetime.date]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if hasattr(value, "year") and hasattr(value, "month"):
        return value

    text = str(value).strip()

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    )

    for date_format in formats:
        try:
            return datetime.strptime(text[:10], date_format).date()
        except ValueError:
            continue

    return None


def parse_number(value) -> Optional[float]:
    if value is None:
        return None

    text = (
        str(value)
        .replace("Q", "")
        .replace(",", "")
        .strip()
    )

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def get_or_create_vehicle_type(db: Session) -> VehicleType:
    item = (
        db.query(VehicleType)
        .filter(VehicleType.nombre == "GRANEL")
        .first()
    )

    if item:
        return item

    item = VehicleType(
        nombre="GRANEL",
        descripcion="Tipo automático para tarifario de granel",
        activo="SI",
    )

    db.add(item)
    db.flush()

    return item


def get_or_create_charge_type(db: Session) -> ChargeType:
    item = (
        db.query(ChargeType)
        .filter(ChargeType.nombre == "POR QUINTAL")
        .first()
    )

    if item:
        return item

    item = ChargeType(
        nombre="POR QUINTAL",
        descripcion="Cobro por quintal entregado",
        activo="SI",
    )

    db.add(item)
    db.flush()

    return item


def find_fuel_price(
    db: Session,
    document_date,
) -> Optional[FuelPrice]:
    """
    Obtiene el precio de combustible de la fecha del viaje.

    Si no hay registro exactamente ese día, utiliza el último precio
    anterior o igual a la fecha del viaje.
    """
    if not document_date:
        return None

    return (
        db.query(FuelPrice)
        .filter(FuelPrice.fecha <= document_date)
        .order_by(FuelPrice.fecha.desc())
        .first()
    )


def find_rate_detail(
    db: Session,
    rate_plan_id: int,
    fuel_price: float,
) -> Optional[RatePlanDetail]:
    return (
        db.query(RatePlanDetail)
        .filter(RatePlanDetail.rate_plan_id == rate_plan_id)
        .filter(RatePlanDetail.activo == "SI")
        .filter(RatePlanDetail.combustible_min <= fuel_price)
        .filter(RatePlanDetail.combustible_max >= fuel_price)
        .order_by(RatePlanDetail.combustible_min.asc())
        .first()
    )


def build_route_index(db: Session) -> dict:
    """
    Construye un índice para localizar rápidamente rutas por origen y destino.
    """
    routes = (
        db.query(Route)
        .filter(Route.activo == "SI")
        .all()
    )

    route_index = {}

    for route in routes:
        key = (
            normalize(route.origen),
            normalize(route.destino),
        )

        route_index[key] = route

    return route_index


def resolve_document_route(
    document: Document,
    route_index: dict,
) -> Optional[Route]:
    """
    1. Usa route_id si el viaje ya lo posee.
    2. Si es histórico, busca por origen y destino normalizados.
    """
    if document.route_id:
        for route in route_index.values():
            if route.id == document.route_id:
                return route

    exact_key = (
        normalize(document.origen),
        normalize(document.destino),
    )

    route = route_index.get(exact_key)

    if route:
        return route

    # Fallback controlado para diferencias menores de nombres.
    document_origin = normalize(document.origen)
    document_destination = normalize(document.destino)

    candidates = []

    for key, candidate in route_index.items():
        route_origin, route_destination = key

        origin_matches = (
            document_origin == route_origin
            or document_origin in route_origin
            or route_origin in document_origin
        )

        destination_matches = (
            document_destination == route_destination
            or document_destination in route_destination
            or route_destination in document_destination
        )

        if origin_matches and destination_matches:
            candidates.append(candidate)

    # Solo asignamos automáticamente cuando existe una coincidencia única.
    if len(candidates) == 1:
        return candidates[0]

    return None


def get_plan_for_route(
    db: Session,
    route_id: int,
    document_date,
) -> Optional[RatePlan]:
    query = (
        db.query(RatePlan)
        .filter(RatePlan.route_id == route_id)
        .filter(RatePlan.estado == "ACTIVO")
    )

    if document_date:
        query = (
            query
            .filter(RatePlan.fecha_inicio <= document_date)
            .filter(
                (RatePlan.fecha_fin.is_(None))
                | (RatePlan.fecha_fin >= document_date)
            )
        )

    return (
        query
        .order_by(
            RatePlan.version.desc(),
            RatePlan.fecha_inicio.desc(),
        )
        .first()
    )


def create_or_update_routes_and_tariffs(
    db: Session,
    rows: list[dict],
    vehicle_type_id: int,
    charge_type_id: int,
) -> dict:
    created_routes = 0
    updated_routes = 0
    created_plans = 0
    created_details = 0
    updated_details = 0

    for row in rows:
        origin = normalize(row.get("origen"))
        destination = normalize(row.get("destino"))

        if not origin or not destination:
            continue

        kilometers = parse_number(row.get("kilometraje"))
        prices = row.get("prices") or []

        if len(prices) != len(FUEL_RANGES):
            continue

        route = (
            db.query(Route)
            .filter(Route.origen == origin)
            .filter(Route.destino == destination)
            .first()
        )

        if not route:
            route = Route(
                nombre=f"{origin} - {destination}",
                origen=origin,
                destino=destination,
                distancia_km=kilometers,
                activo="SI",
            )

            db.add(route)
            db.flush()
            created_routes += 1
        else:
            if kilometers is not None:
                route.distancia_km = kilometers

            route.activo = "SI"
            updated_routes += 1

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
                observaciones=(
                    "Importado desde tarifario de arrendados "
                    "para granel 2026"
                ),
            )

            db.add(plan)
            db.flush()
            created_plans += 1

        for index, price_value in enumerate(prices):
            price = parse_number(price_value)

            if price is None:
                continue

            fuel_min, fuel_max = FUEL_RANGES[index]

            detail = (
                db.query(RatePlanDetail)
                .filter(RatePlanDetail.rate_plan_id == plan.id)
                .filter(
                    RatePlanDetail.combustible_min == fuel_min
                )
                .filter(
                    RatePlanDetail.combustible_max == fuel_max
                )
                .first()
            )

            if not detail:
                detail = RatePlanDetail(
                    rate_plan_id=plan.id,
                    combustible_min=fuel_min,
                    combustible_max=fuel_max,
                    peso_min=0,
                    peso_max=999999999,
                    precio_unitario=price,
                    bonificacion_piloto=0,
                    margen_estimado=None,
                    activo="SI",
                )

                db.add(detail)
                created_details += 1
            else:
                detail.precio_unitario = price
                detail.activo = "SI"
                updated_details += 1

    db.flush()

    return {
        "created_routes": created_routes,
        "updated_routes": updated_routes,
        "created_plans": created_plans,
        "created_details": created_details,
        "updated_details": updated_details,
    }


def recalculate_historical_documents(
    db: Session,
    force_recalculate: bool = False,
) -> dict:
    route_index = build_route_index(db)

    query = db.query(Document)

    if not force_recalculate:
        query = query.filter(Document.precio_total.is_(None))

    documents = query.order_by(Document.id.asc()).all()

    updated_documents = 0
    assigned_routes = 0
    failed_documents = []

    for document in documents:
        route = resolve_document_route(
            document=document,
            route_index=route_index,
        )

        if not route:
            failed_documents.append({
                "document_id": document.id,
                "origen": document.origen,
                "destino": document.destino,
                "motivo": (
                    "No se encontró una ruta única por origen y destino."
                ),
            })
            continue

        if document.route_id != route.id:
            document.route_id = route.id
            assigned_routes += 1

        document_date = parse_date(document.fecha)

        if not document_date:
            failed_documents.append({
                "document_id": document.id,
                "motivo": "La fecha del viaje es inválida.",
            })
            continue

        fuel = find_fuel_price(
            db=db,
            document_date=document_date,
        )

        if not fuel:
            failed_documents.append({
                "document_id": document.id,
                "motivo": (
                    f"No existe precio de combustible vigente "
                    f"para {document_date}."
                ),
            })
            continue

        plan = get_plan_for_route(
            db=db,
            route_id=route.id,
            document_date=document_date,
        )

        if not plan:
            failed_documents.append({
                "document_id": document.id,
                "route_id": route.id,
                "motivo": "La ruta no tiene un tarifario vigente.",
            })
            continue

        detail = find_rate_detail(
            db=db,
            rate_plan_id=plan.id,
            fuel_price=float(fuel.precio_galon),
        )

        if not detail:
            failed_documents.append({
                "document_id": document.id,
                "fuel_price": float(fuel.precio_galon),
                "motivo": (
                    "No existe un rango de combustible aplicable."
                ),
            })
            continue

        quintales = parse_number(document.peso_entregado)

        if quintales is None or quintales <= 0:
            failed_documents.append({
                "document_id": document.id,
                "peso_entregado": document.peso_entregado,
                "motivo": "Los quintales entregados son inválidos.",
            })
            continue

        unit_price = float(detail.precio_unitario or 0)
        total_price = round(quintales * unit_price, 2)

        document.fuel_price_id = fuel.id
        document.fuel_price = float(fuel.precio_galon)

        document.rate_plan_id = plan.id
        document.rate_plan_detail_id = detail.id

        document.precio_unitario = unit_price
        document.precio_total = total_price

        document.bonificacion_piloto = float(
            detail.bonificacion_piloto or 0
        )

        document.pricing_version = plan.version or 1

        updated_documents += 1

    db.flush()

    return {
        "processed_documents": len(documents),
        "assigned_routes": assigned_routes,
        "updated_documents": updated_documents,
        "failed_documents": failed_documents,
    }


def import_tariff_rows_and_update_documents(
    db: Session,
    rows: list[dict],
    force_recalculate: bool = False,
):
    """
    Importa rutas y tarifas y luego repara/recalcula viajes históricos.

    Los viajes antiguos sin route_id se enlazan automáticamente por:
    origen + destino.
    """
    try:
        vehicle_type = get_or_create_vehicle_type(db)
        charge_type = get_or_create_charge_type(db)

        tariff_result = create_or_update_routes_and_tariffs(
            db=db,
            rows=rows,
            vehicle_type_id=vehicle_type.id,
            charge_type_id=charge_type.id,
        )

        recalculation_result = recalculate_historical_documents(
            db=db,
            force_recalculate=force_recalculate,
        )

        db.commit()

        return {
            **tariff_result,
            **recalculation_result,
        }

    except Exception:
        db.rollback()
        raise