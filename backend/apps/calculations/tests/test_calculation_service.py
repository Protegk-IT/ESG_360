from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.calculations.models import (
    EmissionFactor,
    EmissionFactorSource,
)
from apps.calculations.services.calculations import CalculationService
from apps.datapoints.models import Unit, UnitFamily


class CalculationServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.calculation_date = date(2026, 8, 21)

        cls.energy_family = UnitFamily.objects.create(
            code="ENERGY",
            name="Energy",
        )

        cls.volume_family = UnitFamily.objects.create(
            code="VOLUME",
            name="Volume",
        )

        cls.mass_family = UnitFamily.objects.create(
            code="MASS",
            name="Mass",
        )

        cls.kwh = Unit.objects.create(
            family=cls.energy_family,
            code="KWH",
            name="Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        cls.mwh = Unit.objects.create(
            family=cls.energy_family,
            code="MWH",
            name="Megawatt-hour",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
            is_active=True,
        )

        cls.litre = Unit.objects.create(
            family=cls.volume_family,
            code="L",
            name="Litre",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        cls.kg = Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        cls.source = EmissionFactorSource.objects.create(
            code="TEST_SOURCE",
            name="Test Emission Factor Source",
            publisher="Test Publisher",
            version="1.0",
            is_active=True,
        )

        cls.factor = EmissionFactor.objects.create(
            code="TEST_ENERGY_FACTOR",
            source=cls.source,
            activity_key="ENERGY_TEST",
            input_unit=cls.kwh,
            factor_value=Decimal("2.50"),
            output_unit=cls.kg,
            is_active=True,
        )

    # ---------------------------------------------------------
    # BASIC CALCULATIONS
    # ---------------------------------------------------------

    def test_base_unit_calculation(self):
        result = CalculationService.calculate(
            quantity=Decimal("100"),
            quantity_unit=self.kwh,
            factor=self.factor,
            calculation_date=self.calculation_date,
        )

        self.assertEqual(
            result["normalized_quantity"],
            Decimal("100"),
        )

        self.assertEqual(
            result["calculated_value"],
            Decimal("250"),
        )

    def test_converted_unit_calculation(self):
        result = CalculationService.calculate(
            quantity=Decimal("2"),
            quantity_unit=self.mwh,
            factor=self.factor,
            calculation_date=self.calculation_date,
        )

        self.assertEqual(
            result["normalized_quantity"],
            Decimal("2000"),
        )

        self.assertEqual(
            result["calculated_value"],
            Decimal("5000"),
        )

    # ---------------------------------------------------------
    # UNIT VALIDATION
    # ---------------------------------------------------------

    def test_incompatible_unit_is_rejected(self):
        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.litre,
                factor=self.factor,
                calculation_date=self.calculation_date,
            )

    def test_inactive_quantity_unit_is_rejected(self):
        inactive_unit = Unit.objects.create(
            family=self.energy_family,
            code="INACTIVE_KWH",
            name="Inactive Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=False,
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=inactive_unit,
                factor=self.factor,
                calculation_date=self.calculation_date,
            )


    def test_inactive_factor_input_unit_is_rejected(self):
        inactive_unit = Unit.objects.create(
            family=self.energy_family,
            code="INACTIVE_INPUT_KWH",
            name="Inactive Input Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=False,
            is_active=False,
        )

        factor = EmissionFactor.objects.create(
            code="INACTIVE_INPUT_UNIT_FACTOR",
            source=self.source,
            activity_key="INACTIVE_INPUT_UNIT_TEST",
            input_unit=inactive_unit,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    def test_inactive_factor_output_unit_is_rejected(self):
        inactive_unit = Unit.objects.create(
            family=self.mass_family,
            code="INACTIVE_OUTPUT_KG",
            name="Inactive Output Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=False,
            is_active=False,
        )

        factor = EmissionFactor.objects.create(
            code="INACTIVE_OUTPUT_UNIT_FACTOR",
            source=self.source,
            activity_key="INACTIVE_OUTPUT_UNIT_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=inactive_unit,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    # ---------------------------------------------------------
    # QUANTITY VALIDATION
    # ---------------------------------------------------------

    def test_negative_quantity_is_rejected(self):
        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("-10"),
                quantity_unit=self.kwh,
                factor=self.factor,
                calculation_date=self.calculation_date,
            )

    # ---------------------------------------------------------
    # DECIMAL PRECISION
    # ---------------------------------------------------------

    def test_decimal_calculation(self):
        factor = EmissionFactor.objects.create(
            code="DECIMAL_TEST_FACTOR",
            source=self.source,
            activity_key="DECIMAL_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.675"),
            output_unit=self.kg,
            is_active=True,
        )

        result = CalculationService.calculate(
            quantity=Decimal("10.25"),
            quantity_unit=self.kwh,
            factor=factor,
            calculation_date=self.calculation_date,
        )

        self.assertEqual(
            result["calculated_value"],
            Decimal("27.41875"),
        )

    # ---------------------------------------------------------
    # FACTOR VALIDATION
    # ---------------------------------------------------------

    def test_inactive_factor_is_rejected(self):
        factor = EmissionFactor.objects.create(
            code="INACTIVE_FACTOR",
            source=self.source,
            activity_key="INACTIVE_FACTOR_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    def test_expired_factor_is_rejected(self):
        factor = EmissionFactor.objects.create(
            code="EXPIRED_FACTOR",
            source=self.source,
            activity_key="EXPIRED_FACTOR_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    def test_future_factor_is_rejected(self):
        factor = EmissionFactor.objects.create(
            code="FUTURE_FACTOR",
            source=self.source,
            activity_key="FUTURE_FACTOR_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            effective_from=date(2027, 1, 1),
            effective_to=date(2027, 12, 31),
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    # ---------------------------------------------------------
    # SOURCE VALIDATION
    # ---------------------------------------------------------

    def test_inactive_source_is_rejected(self):
        source = EmissionFactorSource.objects.create(
            code="INACTIVE_SOURCE",
            name="Inactive Source",
            publisher="Test Publisher",
            version="1.0",
            is_active=False,
        )

        factor = EmissionFactor.objects.create(
            code="INACTIVE_SOURCE_FACTOR",
            source=source,
            activity_key="INACTIVE_SOURCE_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    def test_expired_source_is_rejected(self):
        source = EmissionFactorSource.objects.create(
            code="EXPIRED_SOURCE",
            name="Expired Source",
            publisher="Test Publisher",
            version="1.0",
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            is_active=True,
        )

        factor = EmissionFactor.objects.create(
            code="EXPIRED_SOURCE_FACTOR",
            source=source,
            activity_key="EXPIRED_SOURCE_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    def test_future_source_is_rejected(self):
        source = EmissionFactorSource.objects.create(
            code="FUTURE_SOURCE",
            name="Future Source",
            publisher="Test Publisher",
            version="1.0",
            effective_from=date(2027, 1, 1),
            effective_to=date(2027, 12, 31),
            is_active=True,
        )

        factor = EmissionFactor.objects.create(
            code="FUTURE_SOURCE_FACTOR",
            source=source,
            activity_key="FUTURE_SOURCE_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    # ---------------------------------------------------------
    # GEOGRAPHY
    # ---------------------------------------------------------

    def test_geography_mismatch_is_rejected(self):
        factor = EmissionFactor.objects.create(
            code="INDIA_FACTOR",
            source=self.source,
            activity_key="GEOGRAPHY_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            geography="IN",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
                geography="US",
            )

    def test_geography_is_required_for_geographic_factor(self):
        factor = EmissionFactor.objects.create(
            code="INDIA_FACTOR_NO_CONTEXT",
            source=self.source,
            activity_key="GEOGRAPHY_REQUIRED_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            geography="IN",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.kwh,
                factor=factor,
                calculation_date=self.calculation_date,
            )

    def test_matching_geography_is_accepted(self):
        factor = EmissionFactor.objects.create(
            code="INDIA_FACTOR_VALID",
            source=self.source,
            activity_key="GEOGRAPHY_VALID_TEST",
            input_unit=self.kwh,
            factor_value=Decimal("2.50"),
            output_unit=self.kg,
            geography="IN",
            is_active=True,
        )

        result = CalculationService.calculate(
            quantity=Decimal("100"),
            quantity_unit=self.kwh,
            factor=factor,
            calculation_date=self.calculation_date,
            geography="IN",
        )

        self.assertEqual(
            result["calculated_value"],
            Decimal("250"),
        )