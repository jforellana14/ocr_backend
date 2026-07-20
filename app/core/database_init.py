from sqlalchemy import inspect, text

from database import engine
from models import Base


DOCUMENT_COLUMNS = {
    "combustible_consumido": "DOUBLE PRECISION",
    "fuel_price_id": "INTEGER",
    "fuel_price": "DOUBLE PRECISION",
    "rate_plan_id": "INTEGER",
    "rate_plan_detail_id": "INTEGER",
    "precio_unitario": "DOUBLE PRECISION",
    "precio_total": "DOUBLE PRECISION",
    "pricing_version": "INTEGER DEFAULT 1",
    "cliente_id": "INTEGER",
    "truck_id": "INTEGER",
    "route_id": "INTEGER",
    "no_vale": "VARCHAR",
    "distancia_viaje": "DOUBLE PRECISION",
    "bonificacion_piloto": "DOUBLE PRECISION",
}

TRUCK_COLUMNS = {"vehicle_type_id": "INTEGER"}


def _add_missing_columns(table: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns(table)}
    with engine.begin() as connection:
        for name, sql_type in columns.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {sql_type}'))


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns("documents", DOCUMENT_COLUMNS)
    _add_missing_columns("trucks", TRUCK_COLUMNS)
