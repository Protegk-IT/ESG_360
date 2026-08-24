from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.calculations.models import EmissionFactor
from apps.datapoints.models import Unit


class CalculationService:
    """
    Performs deterministic emission-factor calculations.

    The service:
    - accepts explicit calculation context
    - validates factor and source validity
    - validates factor applicability
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
        calculation_date: date,
        geography: str | None = None,
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
        # FACTOR VALIDITY
        # -------------------------------------------------

        if not factor.is_active:
            raise ValidationError(
                {
                    "factor": (
                        "The emission factor is inactive "
                        "and cannot be used for calculation."
                    )
                }
            )

        # -------------------------------------------------
        # SOURCE VALIDITY
        # -------------------------------------------------

        source = factor.source

        if not source.is_active:
            raise ValidationError(
                {
                    "factor": (
                        "The emission factor source is inactive "
                        "and cannot be used for calculation."
                    )
                }
            )

        # -------------------------------------------------
        # FACTOR EFFECTIVE DATE
        # -------------------------------------------------

        if (
            factor.effective_from is not None
            and calculation_date < factor.effective_from
        ):
            raise ValidationError(
                {
                    "factor": (
                        "The emission factor is not effective "
                        "on the calculation date."
                    )
                }
            )

        if (
            factor.effective_to is not None
            and calculation_date > factor.effective_to
        ):
            raise ValidationError(
                {
                    "factor": (
                        "The emission factor is not effective "
                        "on the calculation date."
                    )
                }
            )

        # -------------------------------------------------
        # SOURCE EFFECTIVE DATE
        # -------------------------------------------------

        if (
            source.effective_from is not None
            and calculation_date < source.effective_from
        ):
            raise ValidationError(
                {
                    "factor": (
                        "The emission factor source is not effective "
                        "on the calculation date."
                    )
                }
            )

        if (
            source.effective_to is not None
            and calculation_date > source.effective_to
        ):
            raise ValidationError(
                {
                    "factor": (
                        "The emission factor source is not effective "
                        "on the calculation date."
                    )
                }
            )

        # -------------------------------------------------
        # GEOGRAPHY APPLICABILITY
        # -------------------------------------------------

        if factor.geography:
            if geography is None:
                raise ValidationError(
                    {
                        "geography": (
                            "Geography is required because the "
                            "emission factor has a geographic scope."
                        )
                    }
                )

            if factor.geography != geography:
                raise ValidationError(
                    {
                        "geography": (
                            "The emission factor is not applicable "
                            "to the supplied geography."
                        )
                    }
                )

        # -------------------------------------------------
        # UNIT ACTIVE STATE
        # -------------------------------------------------

        if not quantity_unit.is_active:
            raise ValidationError(
                {
                    "quantity_unit": (
                        "The quantity unit is inactive "
                        "and cannot be used."
                    )
                }
            )

        if not factor.input_unit.is_active:
            raise ValidationError(
                {
                    "factor": (
                        "The factor input unit is inactive "
                        "and cannot be used."
                    )
                }
            )

        if not factor.output_unit.is_active:
            raise ValidationError(
                {
                    "factor": (
                        "The factor output unit is inactive "
                        "and cannot be used."
                    )
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