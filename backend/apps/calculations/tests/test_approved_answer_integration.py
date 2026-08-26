from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import TestCase

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.calculations.models import CalculationResult, CalculationResultStatus, CalculationRule, EmissionFactor, EmissionFactorSource
from apps.calculations.services.approved_answer import ApprovedAnswerCalculationService, CalculationResultService
from apps.companies.models import Company
from apps.data_capture.models import Answer, SubmissionStatus
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import CollectionFrequency, CollectionLevel, Datapoint, DatapointCategory, DatapointDataType, Unit, UnitFamily
from apps.modules.models import ESGPillar, Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod
from apps.calculations.views import get_scoped_answer_or_404


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

        cls.mwh = Unit.objects.create(
        family=cls.energy_family,
        code="MWH",
        name="Megawatt-hour",
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
                calculation_date=date(2027, 8, 22),
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


    def test_identical_calculation_is_idempotent(self):
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

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        calculation = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )

        first = CalculationResultService.persist(
            calculation=calculation,
            actor=self.reviewer,
        )

        second = CalculationResultService.persist(
            calculation=calculation,
            actor=self.reviewer,
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.calculation_version, 1)
        self.assertEqual(second.calculation_version, 1)
        self.assertEqual(
            CalculationResult.objects.filter(
                answer=answer,
            ).count(),
            1,
        )
        self.assertEqual(
            CalculationResult.objects.filter(
                answer=answer,
                status=CalculationResultStatus.CURRENT,
            ).count(),
            1,
        )

    def test_rejects_unsupported_calculation_rule_operation(self):
        self.rule.rule_metadata["operation"] = "future_operation"
        self.rule.save()

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

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        with self.assertRaises(ValidationError):
            ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            )

    def test_rejects_unsupported_calculation_rule_input(self):
        self.rule.rule_metadata["input"] = "some_other_input"
        self.rule.save()

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
        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        with self.assertRaises(ValidationError):
            ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            )

    def test_rejects_unsupported_calculation_rule_factor(self):
        self.rule.rule_metadata["factor"] = "some_other_factor"
        self.rule.save()

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
        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        with self.assertRaises(ValidationError):
            ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            )

    def test_approved_integer_answer_calculates_and_persists(self):
        self.datapoint.data_type = DatapointDataType.INTEGER
        self.datapoint.save()

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
            integer_value=100,
            unit=self.kwh,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        calculation = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )

        result = CalculationResultService.persist(
            calculation=calculation,
            actor=self.reviewer,
        )

        self.assertEqual(
            result.input_quantity,
            Decimal("100"),
        )
        self.assertEqual(
            result.calculated_value,
            Decimal("50"),
        )
        self.assertEqual(
            result.status,
            CalculationResultStatus.CURRENT,
        )

    def test_compatible_unit_conversion(self):
        

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
            decimal_value=Decimal("1"),
            unit=self.mwh,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        calculation = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )

        self.assertEqual(
            calculation["normalized_quantity"],
            Decimal("1000.000000000000000"),
        )

        self.assertEqual(
            calculation["calculated_value"],
            Decimal("500.000000000000000"),
        )


    def test_incompatible_unit_is_rejected(self):
        tonne = Unit.objects.create(
            family=self.mass_family,
            code="TONNE",
            name="Tonne",
            factor_to_base=Decimal("1000"),
            is_base_unit=False,
            is_active=True,
        )

        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=self.site,
            reporting_period=self.period,
            assignee=self.maker,
        )

        submission = request.submission

        # Create a valid M5 Answer first.
        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=self.maker,
            decimal_value=Decimal("100"),
            unit=self.kwh,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        # Deliberately put the Answer into an incompatible
        # unit state so that M6 validation is tested.
        Answer.objects.filter(
            pk=answer.pk,
        ).update(
            unit=tonne,
        )

        answer.refresh_from_db()

        with self.assertRaises(ValidationError):
            ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=date(2027, 8, 21),
                geography="",
                actor=self.reviewer,
            )

    def test_inactive_unit_is_rejected(self):
        inactive_kwh = Unit.objects.create(
            family=self.energy_family,
            code="INACTIVE_KWH",
            name="Inactive Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=False,
            is_active=False,
        )

        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=self.site,
            reporting_period=self.period,
            assignee=self.maker,
        )

        submission = request.submission

        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission,
                actor=self.maker,
                decimal_value=Decimal("100"),
                unit=inactive_kwh,
            )

    def test_persisted_result_contains_exact_provenance_snapshots(self):
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

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        calculation = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )

        result = CalculationResultService.persist(
            calculation=calculation,
            actor=self.reviewer,
        )

        self.assertEqual(
            result.calculation_rule_code,
            self.rule.code,
        )
        self.assertEqual(
            result.calculation_rule_name,
            self.rule.name,
        )
        self.assertEqual(
            result.calculation_rule_metadata,
            self.rule.rule_metadata,
        )

        self.assertEqual(
            result.factor_code,
            self.factor.code,
        )
        self.assertEqual(
            result.factor_value,
            self.factor.factor_value,
        )
        self.assertEqual(
            result.factor_source_code,
            self.source.code,
        )
        self.assertEqual(
            result.factor_source_name,
            self.source.name,
        )
        self.assertEqual(
            result.factor_source_version,
            self.source.version,
        )
        self.assertEqual(
            result.factor_source_reference,
            self.source.source_reference,
        )

        self.assertEqual(
            result.input_unit_code,
            self.kwh.code,
        )
        self.assertEqual(
            result.input_unit_name,
            self.kwh.name,
        )
        self.assertEqual(
            result.input_unit_factor_to_base,
            self.kwh.factor_to_base,
        )

        self.assertEqual(
            result.factor_input_unit_code,
            self.factor.input_unit.code,
        )
        self.assertEqual(
            result.factor_input_unit_name,
            self.factor.input_unit.name,
        )
        self.assertEqual(
            result.factor_input_unit_factor_to_base,
            self.factor.input_unit.factor_to_base,
        )

        self.assertEqual(
            result.output_unit_code,
            self.kg.code,
        )
        self.assertEqual(
            result.output_unit_name,
            self.kg.name,
        )

    def test_historical_provenance_survives_live_rule_factor_and_unit_edits(self):
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
            decimal_value=Decimal("1"),
            unit=self.mwh,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        calculation = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )

        result = CalculationResultService.persist(
            calculation=calculation,
            actor=self.reviewer,
        )

        # Capture the historical snapshots stored by M6.
        original_rule_code = result.calculation_rule_code
        original_rule_name = result.calculation_rule_name
        original_rule_metadata = result.calculation_rule_metadata.copy()

        original_factor_code = result.factor_code
        original_factor_value = result.factor_value
        original_source_version = result.factor_source_version

        original_input_unit_code = result.input_unit_code
        original_input_unit_name = result.input_unit_name
        original_input_unit_factor = result.input_unit_factor_to_base

        original_factor_input_unit_code = result.factor_input_unit_code
        original_factor_input_unit_name = result.factor_input_unit_name
        original_factor_input_unit_factor = (
            result.factor_input_unit_factor_to_base
        )

        original_output_unit_code = result.output_unit_code
        original_output_unit_name = result.output_unit_name

        # Change live CalculationRule.
        self.rule.name = "Changed Rule Name"
        self.rule.rule_metadata = {
            "operation": "multiply",
            "input": "activity_quantity",
            "factor": "emission_factor",
            "activity_key": "changed_activity",
        }
        self.rule.save()

        # Change live EmissionFactor.
        self.factor.code = "CHANGED_FACTOR"
        self.factor.factor_value = Decimal("0.75")
        self.factor.save()

        # Change live factor source.
        self.source.version = "2.0"
        self.source.save()

        # Change live Answer input Unit.
        self.mwh.name = "Changed Megawatt-hour"
        self.mwh.factor_to_base = Decimal("2000")
        self.mwh.save()

        # Change live output Unit.
        self.kg.name = "Changed Kilogram"
        self.kg.save(update_fields=["name"])

        # Reload persisted historical result.
        result.refresh_from_db()

        # Rule provenance remains unchanged.
        self.assertEqual(
            result.calculation_rule_code,
            original_rule_code,
        )
        self.assertEqual(
            result.calculation_rule_name,
            original_rule_name,
        )
        self.assertEqual(
            result.calculation_rule_metadata,
            original_rule_metadata,
        )

        # Factor/source provenance remains unchanged.
        self.assertEqual(
            result.factor_code,
            original_factor_code,
        )
        self.assertEqual(
            result.factor_value,
            original_factor_value,
        )
        self.assertEqual(
            result.factor_source_version,
            original_source_version,
        )

        # Original input-unit provenance remains unchanged.
        self.assertEqual(
            result.input_unit_code,
            original_input_unit_code,
        )
        self.assertEqual(
            result.input_unit_name,
            original_input_unit_name,
        )
        self.assertEqual(
            result.input_unit_factor_to_base,
            original_input_unit_factor,
        )

        # Factor-input-unit provenance remains unchanged.
        self.assertEqual(
            result.factor_input_unit_code,
            original_factor_input_unit_code,
        )
        self.assertEqual(
            result.factor_input_unit_name,
            original_factor_input_unit_name,
        )
        self.assertEqual(
            result.factor_input_unit_factor_to_base,
            original_factor_input_unit_factor,
        )

        # Output-unit provenance remains unchanged.
        self.assertEqual(
            result.output_unit_code,
            original_output_unit_code,
        )
        self.assertEqual(
            result.output_unit_name,
            original_output_unit_name,
        )


    def test_calculation_does_not_mutate_m5_state(self):
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

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=self.reviewer,
        )

        answer.refresh_from_db()
        submission.refresh_from_db()
        request.refresh_from_db()

        original_answer_value = answer.decimal_value
        original_answer_unit_id = answer.unit_id
        original_submission_status = submission.status
        original_submission_rejection_reason = submission.rejection_reason
        original_request_status = request.status

        calculation = ApprovedAnswerCalculationService.calculate(
            answer=answer,
            calculation_date=date(2027, 8, 21),
            geography="",
            actor=self.reviewer,
        )

        CalculationResultService.persist(
            calculation=calculation,
            actor=self.reviewer,
        )

        answer.refresh_from_db()
        submission.refresh_from_db()
        request.refresh_from_db()

        self.assertEqual(
            answer.decimal_value,
            original_answer_value,
        )
        self.assertEqual(
            answer.unit_id,
            original_answer_unit_id,
        )
        self.assertEqual(
            submission.status,
            original_submission_status,
        )
        self.assertEqual(
            submission.rejection_reason,
            original_submission_rejection_reason,
        )
        self.assertEqual(
            request.status,
            original_request_status,
        )

    def test_out_of_scope_answer_is_protected_404(self):
        other_site = OrgNode.objects.create(
            company=self.company,
            parent=self.root,
            node_type="FACILITY",
            code="SITE-2",
            name="Site 2",
        )

        # This user has:
        # - data.approve on SITE-1
        # - data.manage/data.enter/data.submit on SITE-2
        # There must be no permission + scope union.
        scoped_user = User.objects.create_user(
            username="scope-test-user",
            password="pass",
        )

        UserRoleAssignment.objects.create(
            user=scoped_user,
            role=self.approve_role,
            org_node=self.site,
        )

        UserRoleAssignment.objects.create(
            user=scoped_user,
            role=self.manage_role,
            org_node=other_site,
        )

        # Create an M5 request on SITE-2.
        request = DataCaptureLifecycleService.create_request(
            actor=self.manager,
            datapoint=self.datapoint,
            org_node=other_site,
            reporting_period=self.period,
            assignee=scoped_user,
        )

        submission = request.submission

        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=scoped_user,
            decimal_value=Decimal("100"),
            unit=self.kwh,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=scoped_user,
        )

        # Reviewer has data.approve on SITE-2.
        site2_reviewer = User.objects.create_user(
            username="site2-reviewer",
            password="pass",
        )

        UserRoleAssignment.objects.create(
            user=site2_reviewer,
            role=self.approve_role,
            org_node=other_site,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=site2_reviewer,
        )

        with self.assertRaises(Http404):
            get_scoped_answer_or_404(
                answer.id,
                scoped_user,
            )         