from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.calculations.models import CalculationResult, CalculationResultStatus, CalculationRule, EmissionFactor, EmissionFactorSource
from apps.calculations.services.approved_answer import ApprovedAnswerCalculationService, CalculationResultService
from apps.companies.models import Company
from apps.data_capture.models import SubmissionStatus
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import CollectionFrequency, CollectionLevel, Datapoint, DatapointCategory, DatapointDataType, Unit, UnitFamily
from apps.modules.models import ESGPillar, Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod


class ApprovedAnswerCalculationIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company_name="Calc Co",
            company_code="CALC",
            contact_person="Owner",
            email="owner@test.com",
            mobile_number="1234567890",
        )
        cls.root = OrgNode.objects.get(company=cls.company, parent__isnull=True)
        cls.site = OrgNode.objects.create(
            company=cls.company,
            parent=cls.root,
            node_type="FACILITY",
            code="SITE-1",
            name="Site 1",
        )
        cls.period = ReportingPeriod.objects.create(
            name="FY 2027",
            period_type=PeriodType.ANNUAL,
            start_date=date(2027, 4, 1),
            end_date=date(2028, 3, 31),
        )
        cls.module = Module.objects.create(code="energy", name="Energy", esg_pillar=ESGPillar.E)
        cls.category = DatapointCategory.objects.create(code="M6_CAT", name="M6 Cat", module=cls.module)
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
            code="ELECTRICITY_CONSUMPTION",
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
        cls.manager = User.objects.create_user(username="calc-manager", password="pass")
        cls.maker = User.objects.create_user(username="calc-maker", password="pass")
        cls.reviewer = User.objects.create_user(username="calc-reviewer", password="pass")
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

        cls.manage_role = Role.objects.create(
            role_code="calc-manage",
            role_name="Calc manage",
        )

        cls.manage_role.permissions.add(
            cls.data_manage,
            cls.data_enter,
            cls.data_submit,
        )
        cls.approve_role = Role.objects.create(role_code="calc-approve", role_name="Calc approve")
        cls.approve_role.permissions.add(cls.data_approve)
        UserRoleAssignment.objects.create(user=cls.manager, role=cls.manage_role, org_node=cls.site)
        UserRoleAssignment.objects.create(user=cls.reviewer, role=cls.approve_role, org_node=cls.site)
        UserRoleAssignment.objects.create(user=cls.maker, role=cls.manage_role, org_node=cls.site)

        cls.source = EmissionFactorSource.objects.create(
            code="TEST_SOURCE",
            name="Test Source",
            publisher="Publisher",
            version="1.0",
            is_active=True,
        )
        cls.factor = EmissionFactor.objects.create(
            code="ELEC_FACTOR",
            source=cls.source,
            activity_key="electricity_consumption",
            input_unit=cls.kwh,
            output_unit=cls.kg,
            factor_value=Decimal("0.5"),
            geography="",
            is_active=True,
        )
        cls.rule = CalculationRule.objects.create(
            code="ELEC_RULE",
            name="Electricity rule",
            datapoint=cls.datapoint,
            rule_metadata={
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
                "activity_key": "electricity_consumption",
            },
            is_active=True,
        )

    def test_approved_decimal_answer_calculates_and_persists(self):
        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=self.site,
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
        DataCaptureLifecycleService.approve(submission, actor=self.reviewer)

        calc = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )
        result = CalculationResultService.persist(calculation=calc, actor=self.reviewer)

        self.assertEqual(result.calculation_version, 1)
        self.assertEqual(result.status, CalculationResultStatus.CURRENT)
        self.assertEqual(result.calculated_value, Decimal("50"))
        self.assertEqual(result.output_unit, self.kg)

    def test_repeated_calculation_creates_new_version_and_supersedes_previous(self):
        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=self.site,
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
        DataCaptureLifecycleService.approve(submission, actor=self.reviewer)

        first = CalculationResultService.persist(
            calculation=ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            ),
            actor=self.reviewer,
        )
        second = CalculationResultService.persist(
            calculation=ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            ),
            actor=self.reviewer,
        )

        self.assertEqual(first.calculation_version, 1)
        self.assertEqual(second.calculation_version, 2)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, CalculationResultStatus.SUPERSEDED)
        self.assertEqual(second.status, CalculationResultStatus.CURRENT)
        self.assertEqual(CalculationResult.objects.filter(answer=answer, status=CalculationResultStatus.CURRENT).count(), 1)

    def test_rejects_unapproved_answer(self):
        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=self.site,
            reporting_period=self.period,
            assignee=self.maker,
        )
        submission = request.submission
        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=self.maker,
            decimal_value=Decimal("10"),
            unit=self.kwh,
        )
        with self.assertRaises(ValidationError):
            ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            )
