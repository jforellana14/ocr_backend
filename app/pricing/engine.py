from app.pricing.validator import PricingValidator
from app.pricing.selector import PricingSelector
from app.pricing.calculator import PricingCalculator


class PricingEngine:

    @staticmethod
    def calculate(
        db,
        fecha,
        client_id,
        route_id,
        vehicle_type_id,
        charge_type_id,
        peso
    ):
        """Compatibilidad con el flujo anterior."""
        PricingValidator.validate_input(
            fecha=fecha,
            client_id=client_id,
            route_id=route_id,
            vehicle_type_id=vehicle_type_id,
            charge_type_id=charge_type_id,
            peso=peso
        )

        fuel = PricingSelector.get_fuel_price(db=db, fecha=fecha)
        rate_plan = PricingSelector.get_rate_plan(
            db=db,
            client_id=client_id,
            route_id=route_id,
            vehicle_type_id=vehicle_type_id,
            charge_type_id=charge_type_id,
            fecha=fecha
        )
        detail = PricingSelector.get_rate_plan_detail(
            db=db,
            rate_plan_id=rate_plan.id,
            fuel_price=fuel.precio_galon,
            peso=float(peso)
        )
        return PricingCalculator.calculate(
            fuel=fuel,
            rate_plan=rate_plan,
            rate_plan_detail=detail,
            peso=float(peso)
        )

    @staticmethod
    def calculate_for_route(db, fecha, route_id, peso, client_id=None):
        """Calcula por ruta y fecha sin depender de IDs fijos de tipo de
        vehículo o tipo de cobro. El tarifario importado es la fuente oficial.
        """
        if not fecha:
            raise ValueError("La fecha del viaje es obligatoria.")
        if not route_id:
            raise ValueError("La ruta es obligatoria.")
        if peso is None or float(peso) <= 0:
            raise ValueError("Los quintales entregados deben ser mayores a cero.")

        fuel = PricingSelector.get_fuel_price(db=db, fecha=fecha)
        rate_plan = PricingSelector.get_rate_plan_for_route(
            db=db,
            route_id=route_id,
            client_id=client_id,
            fecha=fecha,
        )
        detail = PricingSelector.get_rate_plan_detail(
            db=db,
            rate_plan_id=rate_plan.id,
            fuel_price=fuel.precio_galon,
            peso=float(peso),
        )
        return PricingCalculator.calculate(
            fuel=fuel,
            rate_plan=rate_plan,
            rate_plan_detail=detail,
            peso=float(peso),
        )
