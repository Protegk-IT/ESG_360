from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from rest_framework.test import APIClient

from apps.accounts.models import (
    Permission,
    Role,
    User,
    UserRoleAssignment,
)
from apps.calculations.models import (
    CalculationResult,
    CalculationResultStatus,
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)
from apps.companies.models import Company
from apps.data_capture.models import Answer, SubmissionStatus
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import CollectionFrequency, CollectionLevel, Datapoint, DatapointCategory, DatapointDataType, Unit, UnitFamily
from apps.modules.models import ESGPillar, Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod


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

        self.assertEqual(
            source.code,
            "TEST_SOURCE",
        )

        self.assertEqual(
            source.version,
            "1.0",
        )

        self.assertTrue(
            source.is_active,
        )

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
            is_active=True,
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

    def test_factor_accepts_units_from_same_family(self):
        """
        Same-family input/output units are not forbidden by M6.

        M6 must not introduce a domain restriction that is not
        supported by the canonical contract.
        """

        factor = EmissionFactor(
            code="SAME_FAMILY_FACTOR",
            source=self.source,
            activity_key="mass_activity",
            input_unit=self.kg,
            output_unit=self.kg,
            factor_value=Decimal("1.5"),
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

        self.assertFalse(
            factor.is_active,
        )


class CalculationRuleTests(TestCase):
    """
    Tests for the M6 declarative CalculationRule metadata contract.

    M6 defines the metadata structure but does not define a fixed
    list of calculation operations.

    Expected shape:

    {
        "operation": "<operation>",
        "input": "<input_reference>",
        "factor": "<factor_reference>"
    }
    """

    def test_rule_creation(self):
        rule = CalculationRule.objects.create(
            code="ACTIVITY_FACTOR_RULE",
            name="Activity Factor Rule",
            description="Declarative activity/factor calculation rule.",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key":"electricity_consumption"
            },
        )

        self.assertEqual(
            rule.code,
            "ACTIVITY_FACTOR_RULE",
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

    def test_rule_accepts_valid_metadata_shape(self):
        rule = CalculationRule(
            code="VALID_RULE",
            name="Valid Rule",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key":"electricity_consumption"
            },
        )

        rule.full_clean()

    def test_rule_does_not_restrict_operation_value(self):
        """
        M6 defines the metadata shape, but does not define the
        supported calculation-operation vocabulary.
        """

        rule = CalculationRule(
            code="FUTURE_OPERATION_RULE",
            name="Future Operation Rule",
            rule_metadata={
                "operation": "future_operation",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key": "electricity_consumption"
            },
        )

        rule.full_clean()

    def test_rule_requires_operation(self):
        rule = CalculationRule(
            code="MISSING_OPERATION",
            name="Missing Operation",
            rule_metadata={
                "input": "activity_quantity",
                "factor": "emission_factor",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_requires_input(self):
        rule = CalculationRule(
            code="MISSING_INPUT",
            name="Missing Input",
            rule_metadata={
                "operation": "multiply",
                "factor": "emission_factor",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_requires_factor(self):
        rule = CalculationRule(
            code="MISSING_FACTOR",
            name="Missing Factor",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_metadata_fields_must_be_strings(self):
        rule = CalculationRule(
            code="INVALID_FIELD_TYPE",
            name="Invalid Field Type",
            rule_metadata={
                "operation": "multiply",
                "input": 123,
                "factor": "emission_factor",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_rejects_expression_configuration(self):
        rule = CalculationRule(
            code="EXPRESSION_RULE",
            name="Expression Rule",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "expression": "quantity * factor",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_rejects_formula_configuration(self):
        rule = CalculationRule(
            code="FORMULA_RULE",
            name="Formula Rule",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "formula": "quantity * factor",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_rejects_python_configuration(self):
        rule = CalculationRule(
            code="PYTHON_RULE",
            name="Python Rule",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "python": "eval(user_input)",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_rejects_unexpected_metadata_field(self):
        rule = CalculationRule(
            code="EXTRA_FIELD_RULE",
            name="Extra Field Rule",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "unknown": "value",
            },
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_rule_code_is_unique(self):
        CalculationRule.objects.create(
            code="ACTIVITY_FACTOR",
            name="Activity Factor",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key":"electricity_consumption"
            },
        )

        duplicate = CalculationRule(
            code="ACTIVITY_FACTOR",
            name="Another Rule",
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key":"electricity_consumption"
            },
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

class CalculationAPITests(TestCase):
    """
    Tests authentication and RBAC behavior for calculation APIs.

    Read operations require authentication.

    Administrative factor operations require:
        emission_factor.manage

    RBAC is tested through the actual project path:

        User
          ↓
        UserRoleAssignment
          ↓
        Role
          ↓
        Permission
    """

    @classmethod
    def setUpTestData(cls):
        cls.calculation_date = date(2026, 8, 21)

        # -----------------------------------------------------
        # UNITS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # SOURCE
        # -----------------------------------------------------

        cls.source = EmissionFactorSource.objects.create(
            code="API_SOURCE",
            name="API Factor Source",
            publisher="Publisher",
            version="1.0",
            is_active=True,
        )

        # -----------------------------------------------------
        # FACTOR
        # -----------------------------------------------------

        cls.factor = EmissionFactor.objects.create(
            code="API_FACTOR",
            source=cls.source,
            activity_key="electricity_consumption",
            input_unit=cls.kwh,
            output_unit=cls.kg,
            factor_value=Decimal("0.5"),
            is_active=True,
        )

        # -----------------------------------------------------
        # USERS
        # -----------------------------------------------------

        # Normal user that will receive the real
        # emission_factor.manage permission through RBAC.
        cls.user = User.objects.create_user(
            username="calculation_user",
            password="test-password",
        )

        # Normal user with no role assignment.
        cls.no_permission_user = User.objects.create_user(
            username="calculation_no_permission",
            password="test-password",
        )

        # Superuser is retained as a separate verification that
        # superuser access still works.
        cls.admin_user = User.objects.create_superuser(
            username="calculation_admin",
            password="test-password",
        )

        # -----------------------------------------------------
        # REAL RBAC ASSIGNMENT
        # -----------------------------------------------------

        # The canonical project permission is:
        #
        # emission_factor.manage
        #
        # and it is already assigned to the esg_manager role
        # in ROLE_PERMISSIONS.

        try:
            cls.esg_manager_role = Role.objects.get(
                role_code="esg_manager",
            )
        except Role.DoesNotExist:
            # The test suite should normally have the canonical
            # RBAC seed data available. If it does not, create the
            # minimum canonical role/permission needed for this test.
            cls.esg_manager_role = Role.objects.create(
                role_code="esg_manager",
                role_name="ESG Manager",
                description="M6 test role",
                is_active=True,
                is_system=True,
            )

        try:
            cls.manage_permission = Permission.objects.get(
                code="emission_factor.manage",
            )
        except Permission.DoesNotExist:
            cls.manage_permission = Permission.objects.create(
                code="emission_factor.manage",
                name="Manage emission factors",
                module_code="emission_factor",
                action="MANAGE",
            )

        cls.esg_manager_role.permissions.add(
            cls.manage_permission,
        )

        UserRoleAssignment.objects.create(
            user=cls.user,
            role=cls.esg_manager_role,
            is_active=True,
        )

    def setUp(self):
        self.client = APIClient()

    # =========================================================
    # AUTHENTICATION
    # =========================================================

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

    def test_unauthenticated_user_cannot_preview_calculation(self):
        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(self.factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    # =========================================================
    # RBAC
    # =========================================================

    def test_user_without_manage_permission_cannot_create_factor(self):
        """
        A normal authenticated user without
        emission_factor.manage must receive 403.
        """

        self.client.force_authenticate(
            user=self.no_permission_user,
        )

        response = self.client.post(
            "/api/calculations/factors/",
            {
                "code": "NO_PERMISSION_FACTOR",
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

    def test_non_superuser_with_manage_permission_can_create_factor(self):
        """
        Proves the actual RBAC path:

            User
              ↓
            UserRoleAssignment
              ↓
            Role
              ↓
            emission_factor.manage

        The user is NOT a superuser.
        """

        self.assertFalse(
            self.user.is_superuser,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/factors/",
            {
                "code": "RBAC_FACTOR",
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
                code="RBAC_FACTOR",
            ).exists()
        )

    def test_admin_can_create_factor(self):
        """
        Superuser access remains supported by the existing
        HasRolePermission implementation.
        """

        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            "/api/calculations/factors/",
            {
                "code": "SUPERUSER_FACTOR",
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
                code="SUPERUSER_FACTOR",
            ).exists()
        )

    # =========================================================
    # CALCULATION PREVIEW
    # =========================================================

    def test_authenticated_user_can_preview_calculation(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(self.factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # Do not depend on DecimalField string formatting.
        self.assertEqual(
            Decimal(response.data["input_quantity"]),
            Decimal("100"),
        )

        self.assertEqual(
            Decimal(response.data["normalized_quantity"]),
            Decimal("100"),
        )

        self.assertEqual(
            Decimal(response.data["calculated_value"]),
            Decimal("50"),
        )

        self.assertEqual(
            response.data["input_unit"],
            self.kwh.id,
        )

        self.assertEqual(
            response.data["output_unit"],
            self.kg.id,
        )

        self.assertEqual(
            response.data["factor"],
            self.factor.id,
        )

    def test_preview_requires_calculation_date(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(self.factor.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "calculation_date",
            response.data["errors"],
        )

    def test_preview_rejects_incompatible_unit(self):
        volume_family = UnitFamily.objects.create(
            code="VOLUME",
            name="Volume",
        )

        litre = Unit.objects.create(
            family=volume_family,
            code="L",
            name="Litre",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(litre.id),
                "factor": str(self.factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_preview_rejects_inactive_factor(self):
        inactive_factor = EmissionFactor.objects.create(
            code="API_INACTIVE_FACTOR",
            source=self.source,
            activity_key="inactive_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            is_active=False,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(inactive_factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "factor",
            response.data["errors"],
        )

    def test_preview_rejects_inactive_source(self):
        inactive_source = EmissionFactorSource.objects.create(
            code="API_INACTIVE_SOURCE",
            name="Inactive API Source",
            publisher="Publisher",
            version="1.0",
            is_active=False,
        )

        factor = EmissionFactor.objects.create(
            code="API_INACTIVE_SOURCE_FACTOR",
            source=inactive_source,
            activity_key="inactive_source_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            is_active=True,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "factor",
            response.data["errors"],
        )

    def test_preview_rejects_expired_factor(self):
        factor = EmissionFactor.objects.create(
            code="API_EXPIRED_FACTOR",
            source=self.source,
            activity_key="expired_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            is_active=True,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "factor",
            response.data["errors"],
        )

    def test_preview_rejects_future_factor(self):
        factor = EmissionFactor.objects.create(
            code="API_FUTURE_FACTOR",
            source=self.source,
            activity_key="future_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            effective_from=date(2027, 1, 1),
            effective_to=date(2027, 12, 31),
            is_active=True,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "factor",
            response.data["errors"],
        )

    # =========================================================
    # SOURCE DATE VALIDITY
    # =========================================================

    def test_preview_rejects_expired_source(self):
        expired_source = EmissionFactorSource.objects.create(
            code="API_EXPIRED_SOURCE",
            name="Expired API Source",
            publisher="Publisher",
            version="1.0",
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            is_active=True,
        )

        factor = EmissionFactor.objects.create(
            code="API_EXPIRED_SOURCE_FACTOR",
            source=expired_source,
            activity_key="expired_source_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            is_active=True,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "factor",
            response.data["errors"],
        )

    def test_preview_rejects_future_source(self):
        future_source = EmissionFactorSource.objects.create(
            code="API_FUTURE_SOURCE",
            name="Future API Source",
            publisher="Publisher",
            version="1.0",
            effective_from=date(2027, 1, 1),
            effective_to=date(2027, 12, 31),
            is_active=True,
        )

        factor = EmissionFactor.objects.create(
            code="API_FUTURE_SOURCE_FACTOR",
            source=future_source,
            activity_key="future_source_activity",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.5"),
            is_active=True,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            "/api/calculations/preview/",
            {
                "quantity": "100",
                "quantity_unit": str(self.kwh.id),
                "factor": str(factor.id),
                "calculation_date": self.calculation_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "factor",
            response.data["errors"],
        )


class CalculationResultApiTests(TestCase):
    """Real API coverage for the approved-answer M6 result flow."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company_name="Result API Co",
            company_code="RAPI",
            contact_person="Owner",
            email="owner@result-api.test",
            mobile_number="1234567890",
        )
        cls.root = OrgNode.objects.get(company=cls.company, parent__isnull=True)
        cls.org_a = OrgNode.objects.create(
            company=cls.company,
            parent=cls.root,
            node_type="FACILITY",
            code="ORG-A",
            name="Org A",
        )
        cls.org_b = OrgNode.objects.create(
            company=cls.company,
            parent=cls.root,
            node_type="FACILITY",
            code="ORG-B",
            name="Org B",
        )

        cls.period = ReportingPeriod.objects.create(
            name="FY 2027",
            period_type=PeriodType.ANNUAL,
            start_date=date(2027, 4, 1),
            end_date=date(2028, 3, 31),
        )

        cls.module = Module.objects.create(
            code="energy",
            name="Energy",
            esg_pillar=ESGPillar.E,
        )
        cls.category = DatapointCategory.objects.create(
            code="M6_RESULT_API",
            name="Result API",
            module=cls.module,
        )

        cls.energy_family = UnitFamily.objects.create(code="ENERGY", name="Energy")
        cls.mass_family = UnitFamily.objects.create(code="MASS", name="Mass")
        cls.kwh = Unit.objects.create(
            family=cls.energy_family,
            code="KWH",
            name="Kilowatt-hour",
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

        cls.datapoint = Datapoint.objects.create(
            code="RESULT_API_ELECTRICITY",
            category=cls.category,
            module=cls.module,
            label="Electricity consumption",
            data_type=DatapointDataType.DECIMAL,
            unit_family=cls.energy_family,
            default_unit=cls.kwh,
            collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.MONTHLY,
            is_required=True,
        )

        cls.manager = User.objects.create_user(username="result-manager", password="pass")
        cls.maker = User.objects.create_user(username="result-maker", password="pass")
        cls.reviewer = User.objects.create_user(username="result-reviewer", password="pass")
        cls.other_reviewer = User.objects.create_user(username="result-other-reviewer", password="pass")

        cls.data_manage = Permission.objects.create(
            code="data.manage",
            name="Manage data",
            module_code="data",
            action="MANAGE",
        )
        cls.data_enter = Permission.objects.create(
            code="data.enter",
            name="Enter data",
            module_code="data",
            action="ENTER",
        )
        cls.data_submit = Permission.objects.create(
            code="data.submit",
            name="Submit data",
            module_code="data",
            action="SUBMIT",
        )
        cls.data_approve = Permission.objects.create(
            code="data.approve",
            name="Approve data",
            module_code="data",
            action="APPROVE",
        )

        cls.manage_role = Role.objects.create(role_code="result-manage", role_name="Result manage")
        cls.manage_role.permissions.add(cls.data_manage, cls.data_enter, cls.data_submit)
        cls.approve_role = Role.objects.create(role_code="result-approve", role_name="Result approve")
        cls.approve_role.permissions.add(cls.data_approve)

        UserRoleAssignment.objects.create(user=cls.manager, role=cls.manage_role, org_node=cls.org_a)
        UserRoleAssignment.objects.create(user=cls.maker, role=cls.manage_role, org_node=cls.org_a)
        UserRoleAssignment.objects.create(user=cls.reviewer, role=cls.approve_role, org_node=cls.org_a)
        UserRoleAssignment.objects.create(user=cls.other_reviewer, role=cls.approve_role, org_node=cls.org_b)

        cls.source = EmissionFactorSource.objects.create(
            code="RESULT_API_SOURCE",
            name="Result API Source",
            publisher="Publisher",
            version="1.0",
            is_active=True,
        )
        cls.factor = EmissionFactor.objects.create(
            code="RESULT_API_FACTOR",
            source=cls.source,
            activity_key="electricity_consumption",
            input_unit=cls.kwh,
            output_unit=cls.kg,
            factor_value=Decimal("0.5"),
            geography="",
            is_active=True,
        )
        cls.rule = CalculationRule.objects.create(
            code="RESULT_API_RULE",
            name="Result API Rule",
            datapoint=cls.datapoint,
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key": "electricity_consumption",
            },
            is_active=True,
        )

    def setUp(self):
        self.client = APIClient()

    def _create_approved_answer(self, *, org_node, assignee, actor, value=Decimal("100"), unit=None):
        request = DataCaptureLifecycleService.create_request(
            actor=actor,
            datapoint=self.datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=assignee,
        )
        submission = request.submission
        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=assignee,
            decimal_value=value,
            unit=unit or self.kwh,
        )
        DataCaptureLifecycleService.submit(submission, actor=assignee)
        DataCaptureLifecycleService.approve(submission, actor=self.reviewer)
        return request, submission, answer

    def test_non_superuser_with_same_assignment_scope_can_calculate_and_retrieve_result(self):
        _, _, answer = self._create_approved_answer(
            org_node=self.org_a,
            assignee=self.maker,
            actor=self.manager,
        )

        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            "/api/calculations/results/create/",
            {
                "answer": str(answer.id),
                "calculation_date": "2027-08-21",
                "geography": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        result = CalculationResult.objects.get(pk=response.data["id"])
        self.assertEqual(result.calculation_version, 1)
        self.assertEqual(result.status, CalculationResultStatus.CURRENT)
        self.assertEqual(Decimal(response.data["calculated_value"]), Decimal("50"))
        self.assertEqual(Decimal(response.data["normalized_quantity"]), Decimal("100"))

        retrieve = self.client.get(f"/api/calculations/results/{result.id}/")
        self.assertEqual(retrieve.status_code, 200)
        self.assertEqual(str(retrieve.data["id"]), str(result.id))
        self.assertEqual(retrieve.data["status"], CalculationResultStatus.CURRENT)
        self.assertEqual(retrieve.data["calculation_version"], 1)
        self.assertEqual(retrieve.data["org_node"], self.org_a.id)
        self.assertEqual(retrieve.data["factor_source_code"], self.source.code)

    def test_result_create_rejects_unapproved_answer_and_wrong_scope(self):
        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=self.org_a,
            reporting_period=self.period,
            assignee=self.maker,
        )
        submission = request.submission
        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=self.maker,
            decimal_value=Decimal("100"),
            unit=self.kwh,
        )
        DataCaptureLifecycleService.submit(submission, actor=self.maker)

        self.client.force_authenticate(user=self.reviewer)
        unapproved = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(answer.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        self.assertEqual(unapproved.status_code, 400)

        org_b_maker = User.objects.create_user(username="org-b-maker", password="pass")
        UserRoleAssignment.objects.create(user=org_b_maker, role=self.manage_role, org_node=self.org_b)

        other_answer = self._create_approved_answer(
            org_node=self.org_b,
            assignee=org_b_maker,
            actor=self.manager,
        )[2]

        scoped = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(other_answer.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        self.assertEqual(scoped.status_code, 404)

    def test_result_create_rejects_domain_errors_via_api(self):
        _, _, answer = self._create_approved_answer(
            org_node=self.org_a,
            assignee=self.maker,
            actor=self.manager,
        )

        self.client.force_authenticate(user=self.reviewer)

        unit = Unit.objects.create(
            family=self.mass_family,
            code="TONNE",
            name="Tonne",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
            is_active=True,
        )
        Answer.objects.filter(pk=answer.pk).update(unit=unit)
        answer.refresh_from_db()
        incompatible = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(answer.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        self.assertEqual(incompatible.status_code, 400)

        self.factor.activity_key = "different_activity"
        self.factor.save(update_fields=["activity_key"])

        org_b = OrgNode.objects.create(
            company=self.company,
            parent=self.root,
            node_type="FACILITY",
            code="ORG-B-NO-MATCH",
            name="Org B no match",
        )
        org_b_maker = User.objects.create_user(username="org-b-no-match-maker", password="pass")
        UserRoleAssignment.objects.create(user=self.manager, role=self.manage_role, org_node=org_b)
        UserRoleAssignment.objects.create(user=org_b_maker, role=self.manage_role, org_node=org_b)
        UserRoleAssignment.objects.create(user=self.reviewer, role=self.approve_role, org_node=org_b)

        no_match_request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=org_b,
            reporting_period=self.period,
            assignee=org_b_maker,
        )
        no_match_submission = no_match_request.submission
        answer2 = DataCaptureLifecycleService.save_scalar_answer(
            no_match_submission,
            actor=org_b_maker,
            decimal_value=Decimal("80"),
            unit=self.kwh,
        )
        DataCaptureLifecycleService.submit(no_match_submission, actor=org_b_maker)
        DataCaptureLifecycleService.approve(no_match_submission, actor=self.reviewer)
        no_match = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(answer2.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        self.assertEqual(no_match.status_code, 400)

        self.factor.activity_key = "electricity_consumption"
        self.factor.save(update_fields=["activity_key"])
        duplicate = EmissionFactor.objects.create(
            code="RESULT_API_FACTOR_DUPLICATE",
            source=self.source,
            activity_key="electricity_consumption",
            input_unit=self.kwh,
            output_unit=self.kg,
            factor_value=Decimal("0.75"),
            geography="",
            is_active=True,
        )
        self.assertIsNotNone(duplicate)

        org_c = OrgNode.objects.create(
            company=self.company,
            parent=self.root,
            node_type="FACILITY",
            code="ORG-C-AMBIGUOUS",
            name="Org C ambiguous",
        )
        org_c_maker = User.objects.create_user(username="org-c-ambiguous-maker", password="pass")
        UserRoleAssignment.objects.create(user=self.manager, role=self.manage_role, org_node=org_c)
        UserRoleAssignment.objects.create(user=org_c_maker, role=self.manage_role, org_node=org_c)
        UserRoleAssignment.objects.create(user=self.reviewer, role=self.approve_role, org_node=org_c)

        ambiguous_request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=org_c,
            reporting_period=self.period,
            assignee=org_c_maker,
        )
        ambiguous_submission = ambiguous_request.submission
        answer3 = DataCaptureLifecycleService.save_scalar_answer(
            ambiguous_submission,
            actor=org_c_maker,
            decimal_value=Decimal("60"),
            unit=self.kwh,
        )
        DataCaptureLifecycleService.submit(ambiguous_submission, actor=org_c_maker)
        DataCaptureLifecycleService.approve(ambiguous_submission, actor=self.reviewer)
        ambiguous = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(answer3.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        self.assertEqual(ambiguous.status_code, 400)

    def test_result_api_protects_wrong_scope_result_and_preserves_m5_state(self):
        _, _, answer = self._create_approved_answer(
            org_node=self.org_a,
            assignee=self.maker,
            actor=self.manager,
        )
        self.client.force_authenticate(user=self.reviewer)
        create_response = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(answer.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        result = CalculationResult.objects.get(pk=create_response.data["id"])
        answer.refresh_from_db()
        submission = result.submission
        submission.refresh_from_db()
        request = result.data_request
        request.refresh_from_db()

        self.assertEqual(answer.decimal_value, Decimal("100"))
        self.assertEqual(answer.unit_id, self.kwh.id)
        self.assertEqual(submission.status, SubmissionStatus.APPROVED)
        self.assertEqual(request.status, "COMPLETED")

        other_user = User.objects.create_user(username="result-scope-user", password="pass")
        UserRoleAssignment.objects.create(user=other_user, role=self.approve_role, org_node=self.org_b)
        self.client.force_authenticate(user=other_user)
        protected = self.client.get(f"/api/calculations/results/{result.id}/")
        self.assertEqual(protected.status_code, 404)

    def test_calculation_result_mutation_routes_are_405(self):
        _, _, answer = self._create_approved_answer(
            org_node=self.org_a,
            assignee=self.maker,
            actor=self.manager,
        )
        self.client.force_authenticate(user=self.reviewer)
        create_response = self.client.post(
            "/api/calculations/results/create/",
            {"answer": str(answer.id), "calculation_date": "2027-08-21"},
            format="json",
        )
        result = CalculationResult.objects.get(pk=create_response.data["id"])

        response = self.client.post("/api/calculations/results/", {"answer": str(answer.id)}, format="json")
        self.assertEqual(response.status_code, 405)

        put_response = self.client.put(f"/api/calculations/results/{result.id}/", {"answer": str(answer.id)}, format="json")
        self.assertEqual(put_response.status_code, 405)

        patch_response = self.client.patch(f"/api/calculations/results/{result.id}/", {"answer": str(answer.id)}, format="json")
        self.assertEqual(patch_response.status_code, 405)

        delete_response = self.client.delete(f"/api/calculations/results/{result.id}/")
        self.assertEqual(delete_response.status_code, 405)


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

        cls.kwh = Unit.objects.create(
            family=cls.energy_family,
            code="KWH",
            name="Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        cls.module = Module.objects.create(
            code="energy",
            name="Energy",
            esg_pillar=ESGPillar.E,
        )

        cls.category = DatapointCategory.objects.create(
            code="ENERGY",
            name="Energy",
            module=cls.module,
        )

        cls.datapoint = Datapoint.objects.create(
            code="ENERGY_TOTAL_CONSUMPTION",
            category=cls.category,
            module=cls.module,
            label="Total energy consumption",
            data_type=DatapointDataType.DECIMAL,
            unit_family=cls.energy_family,
            default_unit=cls.kwh,
            collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.MONTHLY,
            is_required=False,
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

        cls.l = Unit.objects.create(
            family=cls.volume_family,
            code="L",
            name="Litre",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
            is_active=True,
        )

        cls.m3 = Unit.objects.create(
            family=cls.volume_family,
            code="M3",
            name="Cubic metre",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
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

        cls.tonne = Unit.objects.create(
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