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
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)
from apps.datapoints.models import CollectionFrequency, CollectionLevel, Datapoint, DatapointCategory, DatapointDataType, Unit, UnitFamily
from apps.modules.models import ESGPillar, Module


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