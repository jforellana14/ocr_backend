from app.pricing.exceptions import MissingPricingDataError


class PricingValidator:

    @staticmethod
    def validate_input(
        fecha,
        client_id,
        route_id,
        vehicle_type_id,
        charge_type_id,
        peso
    ):
        if not fecha:
            raise MissingPricingDataError("La fecha del viaje es obligatoria.")

        if not client_id:
            raise MissingPricingDataError("El cliente es obligatorio.")

        if not route_id:
            raise MissingPricingDataError("La ruta es obligatoria.")

        if not vehicle_type_id:
            raise MissingPricingDataError("El tipo de vehículo es obligatorio.")

        if not charge_type_id:
            raise MissingPricingDataError("El tipo de cobro es obligatorio.")

        if peso is None or float(peso) <= 0:
            raise MissingPricingDataError("El peso debe ser mayor a cero.")

        return True