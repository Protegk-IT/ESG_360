from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.calculations.models import EmissionFactor
from apps.datapoints.models import Unit


class CalculationService:
    """
    Performs deterministic emission-factor calculations.

    The service:
    - accepts explicit calculation inputs
    - validates unit compatibility
    - converts the input quantity to the factor's expected unit
    - performs Decimal-safe multiplication
    - does not persist calculation results
    - does not depend on M5 Answer models
    """

    @staticmethod
    def calculate(*, quantity,
        quantity_unit: Unit,
        factor: EmissionFactor,
    ) -> dict:
        quantity = Decimal(str(quantity))

        # -------------------------------------------------
        # QUANTITY VALIDATION
        # -------------------------------------------------

        if quantity < Decimal("0"):
            raise ValidationError(
                {
                    "quantity": "Quantity cannot be negative."
                }
            )

        # -------------------------------------------------
        # UNIT COMPATIBILITY
        # -------------------------------------------------

        if quantity_unit.family_id != factor.input_unit.family_id:
            raise ValidationError(
                {
                    "quantity_unit": (
                        "Quantity unit is not compatible with "
                        "the emission factor input unit family."
                    )
                }
            )

        # -------------------------------------------------
        # CONVERT INPUT TO FACTOR UNIT
        # -------------------------------------------------

        quantity_in_factor_unit = (
            quantity * quantity_unit.factor_to_base
        ) / factor.input_unit.factor_to_base

        # -------------------------------------------------
        # CALCULATE RESULT
        # -------------------------------------------------

        result = quantity_in_factor_unit * factor.factor_value

        return {
            "input_quantity": quantity,
            "input_unit": quantity_unit,
            "normalized_quantity": quantity_in_factor_unit,
            "calculated_value": result,
            "output_unit": factor.output_unit,
            "factor": factor,
        }