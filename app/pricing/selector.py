from app.pricing.exceptions import (
    FuelPriceNotFoundError,
    RatePlanNotFoundError,
    RatePlanDetailNotFoundError,
    MultipleRatePlanDetailsFoundError,
)

from models import FuelPrice, RatePlan, RatePlanDetail


class PricingSelector:

    @staticmethod
    def get_fuel_price(db, fecha):

        fuel = (
            db.query(FuelPrice)
            .filter(FuelPrice.fecha <= fecha)
            .order_by(FuelPrice.fecha.desc())
            .first()
        )

        if not fuel:
            raise FuelPriceNotFoundError(
                f"No existe precio de combustible para {fecha}."
            )

        return fuel

    @staticmethod
    def get_rate_plan(
        db,
        client_id,
        route_id,
        vehicle_type_id,
        charge_type_id,
        fecha
    ):

        base_query = (
            db.query(RatePlan)
            .filter(RatePlan.estado == "ACTIVO")
            .filter(RatePlan.route_id == route_id)
            .filter(RatePlan.vehicle_type_id == vehicle_type_id)
            .filter(RatePlan.charge_type_id == charge_type_id)
            .filter(RatePlan.fecha_inicio <= fecha)
            .filter(
                (RatePlan.fecha_fin == None) |
                (RatePlan.fecha_fin >= fecha)
            )
        )

        plan = (
            base_query
            .filter(RatePlan.client_id == client_id)
            .first()
        )

        if not plan:
            plan = (
                base_query
                .filter(RatePlan.client_id == None)
                .first()
            )

        if not plan:
            raise RatePlanNotFoundError(
                "No existe un tarifario activo para esta combinación."
            )

        return plan


    @staticmethod
    def get_rate_plan_for_route(db, route_id, fecha, client_id=None):
        base_query = (
            db.query(RatePlan)
            .filter(RatePlan.estado == "ACTIVO")
            .filter(RatePlan.route_id == route_id)
            .filter(RatePlan.fecha_inicio <= fecha)
            .filter((RatePlan.fecha_fin == None) | (RatePlan.fecha_fin >= fecha))
        )

        plan = None
        if client_id:
            plan = (
                base_query
                .filter(RatePlan.client_id == client_id)
                .order_by(RatePlan.version.desc(), RatePlan.fecha_inicio.desc())
                .first()
            )

        if not plan:
            plan = (
                base_query
                .filter(RatePlan.client_id == None)
                .order_by(RatePlan.version.desc(), RatePlan.fecha_inicio.desc())
                .first()
            )

        if not plan:
            # Respaldo para tarifarios antiguos con client_id poblado.
            plan = (
                base_query
                .order_by(RatePlan.version.desc(), RatePlan.fecha_inicio.desc())
                .first()
            )

        if not plan:
            raise RatePlanNotFoundError(
                "La ruta no tiene un tarifario activo para la fecha del viaje."
            )

        return plan

    @staticmethod
    def get_rate_plan_detail(
        db,
        rate_plan_id,
        fuel_price,
        peso
    ):

        details = (
            db.query(RatePlanDetail)
            .filter(RatePlanDetail.rate_plan_id == rate_plan_id)
            .filter(RatePlanDetail.activo == "SI")
            .filter(RatePlanDetail.combustible_min <= fuel_price)
            .filter(RatePlanDetail.combustible_max >= fuel_price)
            .filter(RatePlanDetail.peso_min <= peso)
            .filter(RatePlanDetail.peso_max >= peso)
            .all()
        )

        if len(details) == 0:
            raise RatePlanDetailNotFoundError(
                "No existe un rango que aplique."
            )

        if len(details) > 1:
            raise MultipleRatePlanDetailsFoundError(
                "Existen múltiples rangos para el mismo viaje."
            )

        return details[0]