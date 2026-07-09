class PricingError(Exception):
    pass


class MissingPricingDataError(PricingError):
    pass


class FuelPriceNotFoundError(PricingError):
    pass


class RatePlanNotFoundError(PricingError):
    pass


class RatePlanDetailNotFoundError(PricingError):
    pass


class MultipleRatePlanDetailsFoundError(PricingError):
    pass