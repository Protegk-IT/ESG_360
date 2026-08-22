from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.calculations.models import EmissionFactor, EmissionFactorSource
from apps.calculations.services.calculations import CalculationService
from apps.datapoints.models import Unit, UnitFamily


class CalculationServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
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
        )

        cls.mwh = Unit.objects.create(
            family=cls.energy_family,
            code="MWH",
            name="Megawatt-hour",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
        )

        cls.litre = Unit.objects.create(
            family=cls.volume_family,
            code="L",
            name="Litre",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

        cls.kg = Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
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

    def test_base_unit_calculation(self):
        result = CalculationService.calculate(
            quantity=Decimal("100"),
            quantity_unit=self.kwh,
            factor=self.factor,
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
        )

        self.assertEqual(
            result["normalized_quantity"],
            Decimal("2000"),
        )

        self.assertEqual(
            result["calculated_value"],
            Decimal("5000"),
        )

    def test_incompatible_unit_is_rejected(self):
        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("100"),
                quantity_unit=self.litre,
                factor=self.factor,
            )

    def test_negative_quantity_is_rejected(self):
        with self.assertRaises(ValidationError):
            CalculationService.calculate(
                quantity=Decimal("-10"),
                quantity_unit=self.kwh,
                factor=self.factor,
            )

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
        )

        self.assertEqual(
        result["calculated_value"],
        Decimal("27.41875"),
)