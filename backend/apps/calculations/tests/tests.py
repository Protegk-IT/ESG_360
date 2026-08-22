from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.calculations.models import (
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)
from apps.datapoints.models import UnitFamily, Unit


class EmissionFactorSourceTests(TestCase):
    """
    Tests for emission-factor source/version metadata.
    """

    def test_source_version_creation(self):
        source = EmissionFactorSource.objects.create(
            code="TEST_SOURCE",
            name="Test Factor Source",
            publisher="Test Publisher",
            version="1.0",
        )

        self.assertEqual(source.code, "TEST_SOURCE")
        self.assertEqual(source.version, "1.0")
        self.assertTrue(source.is_active)

    def test_source_rejects_invalid_effective_date_range(self):
        source = EmissionFactorSource(
            code="INVALID_DATE_SOURCE",
            name="Invalid Date Source",
            publisher="Test Publisher",
            version="1.0",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError):
            source.full_clean()

    def test_source_code_and_version_are_unique(self):
        EmissionFactorSource.objects.create(
            code="SOURCE_001",
            name="Source",
            publisher="Publisher",
            version="1.0",
        )

        duplicate = EmissionFactorSource(
            code="SOURCE_001",
            name="Another Source",
            publisher="Publisher",
            version="1.0",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class EmissionFactorTests(TestCase):
    """
    Tests for emission-factor validation and M4 unit compatibility.
    """

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
            is_base_unit=True,
            factor_to_base=Decimal("1"),
            is_active=True,
        )

        cls.mwh = Unit.objects.create(
            family=cls.energy_family,
            code="MWH",
            name="Megawatt-hour",
            is_base_unit=False,
            factor_to_base=Decimal("1000"),
            is_active=True,
        )

        cls.kg = Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            is_base_unit=True,
            factor_to_base=Decimal("1"),
            is_active=True,
        )

        cls.source = EmissionFactorSource.objects.create(
            code="SOURCE_001",
            name="Factor Source",
            publisher="Publisher",
            version="1.0",
        )

    def test_factor_creation(self):
        factor = EmissionFactor.objects.create(
            code="ELECTRICITY_FACTOR",
            source=self.source,
            activity_key="electricity_consumption",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.500000000000000"),
        )

        self.assertEqual(
            factor.factor_value,
            Decimal("0.500000000000000"),
        )

    def test_factor_value_must_be_positive(self):
        factor = EmissionFactor(
            code="ZERO_FACTOR",
            source=self.source,
            activity_key="electricity_consumption",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0"),
        )

        with self.assertRaises(ValidationError):
            factor.full_clean()

    def test_negative_factor_value_is_rejected(self):
        factor = EmissionFactor(
            code="NEGATIVE_FACTOR",
            source=self.source,
            activity_key="electricity_consumption",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("-1"),
        )

        with self.assertRaises(ValidationError):
            factor.full_clean()

    def test_factor_rejects_invalid_effective_date_range(self):
        factor = EmissionFactor(
            code="INVALID_DATE_FACTOR",
            source=self.source,
            activity_key="electricity_consumption",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError):
            factor.full_clean()

    def test_factor_accepts_units_from_different_families(self):
        factor = EmissionFactor(
            code="VALID_UNIT_FACTOR",
            source=self.source,
            activity_key="electricity_consumption",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
        )

        factor.full_clean()


    def test_inactive_factor_is_stored_as_inactive(self):
        factor = EmissionFactor.objects.create(
            code="INACTIVE_FACTOR",
            source=self.source,
            activity_key="inactive_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("1.5"),
            is_active=False,
        )

        self.assertFalse(factor.is_active)


class CalculationRuleTests(TestCase):
    """
    Tests for declarative calculation-rule metadata.
    """

    def test_rule_creation(self):
        rule = CalculationRule.objects.create(
            code="ACTIVITY_FACTOR_MULTIPLICATION",
            name="Activity × Factor",
            description="Multiply normalized activity by selected factor.",
            rule_metadata={
                "operation": "multiply",
            },
        )

        self.assertEqual(
            rule.code,
            "ACTIVITY_FACTOR_MULTIPLICATION",
        )

    def test_rule_metadata_must_be_json_object(self):
        rule = CalculationRule(
            code="INVALID_RULE",
            name="Invalid Rule",
            rule_metadata=[
                "multiply",
            ],
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_accepts_declarative_metadata(self):
        rule = CalculationRule(
            code="VALID_RULE",
            name="Activity × Factor",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
            },
        )

        rule.full_clean()

    def test_rule_code_is_unique(self):
        CalculationRule.objects.create(
            code="ACTIVITY_FACTOR",
            name="Activity Factor",
            rule_metadata={
                "operation": "multiply",
            },
        )

        duplicate = CalculationRule(
            code="ACTIVITY_FACTOR",
            name="Another Rule",
            rule_metadata={
                "operation": "multiply",
            },
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class CalculationAPITests(TestCase):
    """
    Tests authentication and RBAC behavior for calculation APIs.

    Read operations require authentication.
    Administrative operations require emission_factor.manage.
    """

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
            is_base_unit=True,
            factor_to_base=Decimal("1"),
            is_active=True,
        )

        cls.kg = Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            is_base_unit=True,
            factor_to_base=Decimal("1"),
            is_active=True,
        )

        cls.source = EmissionFactorSource.objects.create(
            code="API_SOURCE",
            name="API Factor Source",
            publisher="Publisher",
            version="1.0",
        )

        cls.factor = EmissionFactor.objects.create(
            code="API_FACTOR",
            source=cls.source,
            activity_key="electricity_consumption",
            input_unit=cls.kwh,
            output_unit=cls.kg,
            factor_value=Decimal("0.5"),
        )

        cls.user = User.objects.create_user(
            username="calculation_user",
            password="test-password",
        )

        cls.admin_user = User.objects.create_superuser(
            username="calculation_admin",
            password="test-password",
        )

    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_user_cannot_access_factors(self):
        response = self.client.get(
            "/api/calculations/factors/"
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_authenticated_user_can_read_factors(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.get(
            "/api/calculations/factors/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_user_without_manage_permission_cannot_create_factor(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/factors/",
            {
                "code": "NEW_FACTOR",
                "source": str(self.source.id),
                "activity_key": "electricity_consumption",
                "input_unit": str(self.kwh.id),
                "output_unit": str(self.kg.id),
                "factor_value": "0.5",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_admin_can_create_factor(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            "/api/calculations/factors/",
            {
                "code": "NEW_FACTOR",
                "source": str(self.source.id),
                "activity_key": "electricity_consumption",
                "input_unit": str(self.kwh.id),
                "output_unit": str(self.kg.id),
                "factor_value": "0.5",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            EmissionFactor.objects.filter(
                code="NEW_FACTOR",
            ).exists()
        )


class SeedCommandTests(TestCase):
    """
    Tests that the emission-factor seed command is idempotent.

    M6 consumes the M4 unit registry. The required M4 units are
    created here as test prerequisites and are not created by M6.
    """

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

        Unit.objects.create(
            family=cls.energy_family,
            code="KWH",
            name="Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        Unit.objects.create(
            family=cls.energy_family,
            code="MWH",
            name="Megawatt-hour",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
            is_active=True,
        )

        Unit.objects.create(
            family=cls.volume_family,
            code="L",
            name="Litre",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        Unit.objects.create(
            family=cls.volume_family,
            code="M3",
            name="Cubic metre",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
            is_active=True,
        )

        Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        Unit.objects.create(
            family=cls.mass_family,
            code="TONNE",
            name="Tonne",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
            is_active=True,
        )

    def test_seed_command_is_idempotent(self):
        first_output = StringIO()

        call_command(
            "seed_emission_factors",
            stdout=first_output,
        )

        source_count = EmissionFactorSource.objects.count()
        factor_count = EmissionFactor.objects.count()
        rule_count = CalculationRule.objects.count()

        second_output = StringIO()

        call_command(
            "seed_emission_factors",
            stdout=second_output,
        )

        self.assertEqual(
            EmissionFactorSource.objects.count(),
            source_count,
        )

        self.assertEqual(
            EmissionFactor.objects.count(),
            factor_count,
        )

        self.assertEqual(
            CalculationRule.objects.count(),
            rule_count,
        )

class MigrationTests(TestCase):
    """
    Verifies that model changes have corresponding migrations.
    """

    def test_no_pending_model_migrations(self):
        output = StringIO()

        call_command(
            "makemigrations",
            "--check",
            "--dry-run",
            stdout=output,
            stderr=output,
        )

        self.assertNotIn(
            "Migrations for",
            output.getvalue(),
        )