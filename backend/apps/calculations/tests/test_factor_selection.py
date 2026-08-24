from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.calculations.models import (
    EmissionFactor,
    EmissionFactorSource,
)
from apps.calculations.services.factor_selection import FactorSelectionService
from apps.datapoints.models import Unit, UnitFamily


class FactorSelectionServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.energy_family = UnitFamily.objects.create(
            code="ENERGY",
            name="Energy",
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

        cls.kg = Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

        cls.source = EmissionFactorSource.objects.create(
            code="TEST_SOURCE",
            name="Test Source",
            publisher="Test Publisher",
            version="1.0",
            is_active=True,
        )

    def create_factor(
        self,
        *,
        code,
        activity_key="DIESEL",
        geography="IN",
        effective_from=None,
        effective_to=None,
        is_active=True,
        source=None,
    ):
        return EmissionFactor.objects.create(
            code=code,
            source=source or self.source,
            activity_key=activity_key,
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("2.50"),
            geography=geography,
            effective_from=effective_from,
            effective_to=effective_to,
            is_active=is_active,
        )

    def test_selects_matching_active_factor(self):
        factor = self.create_factor(
            code="DIESEL_IN",
        )

        result = FactorSelectionService.select_factor(
            activity_key="DIESEL",
            geography="IN",
        )

        self.assertEqual(result, factor)

    def test_inactive_factor_is_not_selected(self):
        self.create_factor(
            code="DIESEL_INACTIVE",
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
            )

    def test_no_matching_factor_raises_error(self):
        self.create_factor(
            code="DIESEL_IN",
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="PETROL",
                geography="IN",
            )

    def test_ambiguous_factor_selection_raises_error(self):
        self.create_factor(
            code="DIESEL_IN_1",
        )

        self.create_factor(
            code="DIESEL_IN_2",
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
            )

    def test_factor_effective_on_requested_date_is_selected(self):
        factor = self.create_factor(
            code="DIESEL_2026",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )

        result = FactorSelectionService.select_factor(
            activity_key="DIESEL",
            geography="IN",
            calculation_date=date(2026, 8, 21),
        )

        self.assertEqual(result, factor)

    def test_expired_factor_is_not_selected(self):
        self.create_factor(
            code="DIESEL_EXPIRED",
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
                calculation_date=date(2026, 8, 21),
            )

    def test_factor_not_yet_effective_is_not_selected(self):
        self.create_factor(
            code="DIESEL_FUTURE",
            effective_from=date(2027, 1, 1),
            effective_to=date(2027, 12, 31),
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
                calculation_date=date(2026, 8, 21),
            )

    def test_factor_without_effective_dates_can_be_selected(self):
        factor = self.create_factor(
            code="DIESEL_NO_DATES",
        )

        result = FactorSelectionService.select_factor(
            activity_key="DIESEL",
            geography="IN",
            calculation_date=date(2026, 8, 21),
        )

        self.assertEqual(result, factor)

    def test_inactive_source_is_not_selected(self):
        inactive_source = EmissionFactorSource.objects.create(
            code="INACTIVE_SOURCE",
            name="Inactive Source",
            publisher="Test Publisher",
            version="1.0",
            is_active=False,
        )

        self.create_factor(
            code="DIESEL_INACTIVE_SOURCE",
            source=inactive_source,
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
                calculation_date=date(2026, 8, 21),
            )

    def test_expired_source_is_not_selected(self):
        expired_source = EmissionFactorSource.objects.create(
            code="EXPIRED_SOURCE",
            name="Expired Source",
            publisher="Test Publisher",
            version="1.0",
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            is_active=True,
        )

        self.create_factor(
            code="DIESEL_EXPIRED_SOURCE",
            source=expired_source,
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
                calculation_date=date(2026, 8, 21),
            )

    def test_future_source_is_not_selected(self):
        future_source = EmissionFactorSource.objects.create(
            code="FUTURE_SOURCE",
            name="Future Source",
            publisher="Test Publisher",
            version="1.0",
            effective_from=date(2027, 1, 1),
            effective_to=date(2027, 12, 31),
            is_active=True,
        )

        self.create_factor(
            code="DIESEL_FUTURE_SOURCE",
            source=future_source,
        )

        with self.assertRaises(ValidationError):
            FactorSelectionService.select_factor(
                activity_key="DIESEL",
                geography="IN",
                calculation_date=date(2026, 8, 21),
            )

    def test_source_without_effective_dates_can_be_selected(self):
        factor = self.create_factor(
            code="DIESEL_SOURCE_NO_DATES",
        )

        result = FactorSelectionService.select_factor(
            activity_key="DIESEL",
            geography="IN",
            calculation_date=date(2026, 8, 21),
        )

        self.assertEqual(result, factor)