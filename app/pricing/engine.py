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
        PricingValidator.validate_input(
            fecha=fecha,
            client_id=client_id,
            route_id=route_id,
            vehicle_type_id=vehicle_type_id,
            charge_type_id=charge_type_id,
            peso=peso
        )

        fuel = PricingSelector.get_fuel_price(
            db=db,
            fecha=fecha
        )

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