from app.pricing.result import PricingResult


class PricingCalculator:

    @staticmethod
    def calculate(
        fuel,
        rate_plan,
        rate_plan_detail,
        peso
    ):
        peso = float(peso)

        precio_unitario = float(
            rate_plan_detail.precio_unitario or 0
        )

        precio_total = peso * precio_unitario

        bonificacion = float(
            rate_plan_detail.bonificacion_piloto or 0
        )

        margen = rate_plan_detail.margen_estimado

        return PricingResult(
            fuel_price_id=fuel.id,
            fuel_price=float(fuel.precio_galon),
            rate_plan_id=rate_plan.id,
            rate_plan_detail_id=rate_plan_detail.id,
            precio_unitario=precio_unitario,
            peso=peso,
            precio_total=precio_total,
            bonificacion=bonificacion,
            margen=margen,
            version=1
        )