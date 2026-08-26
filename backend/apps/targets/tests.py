from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.data_capture.models import Answer, DataRequest, Submission, SubmissionStatus
from apps.datapoints.models import CollectionFrequency, CollectionLevel, Datapoint, DatapointCategory, DatapointDataType, Unit, UnitFamily
from apps.modules.models import Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod
from apps.targets.models import Goal, KPI, KPIDirection, KPIAggregation, MetricSourceType, Target
from apps.targets.services.progress import progress_for, trajectory_value


class TargetFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="target-owner", password="x")
        self.company = Company.objects.create(company_name="Target Co", company_code="TARGET", contact_person="Owner", email="owner@example.test", mobile_number="9999999999")
        self.org = OrgNode.objects.get(company=self.company, node_type="LEGAL_ENTITY")
        self.module = Module.objects.create(code="environment", name="Environment")
        self.category = DatapointCategory.objects.create(code="energy", name="Energy", module=self.module)
        self.family = UnitFamily.objects.create(code="ENERGY", name="Energy")
        self.unit = Unit.objects.create(family=self.family, code="KWH_TEST", name="kWh", factor_to_base=Decimal("1"), is_base_unit=True)
        self.datapoint = Datapoint.objects.create(code="energy.total.test", category=self.category, module=self.module, label="Energy", data_type=DatapointDataType.DECIMAL, unit_family=self.family, default_unit=self.unit, collection_level=CollectionLevel.ORG_NODE, frequency=CollectionFrequency.ANNUAL)
        self.baseline = ReportingPeriod.objects.create(name="FY 2025", period_type=PeriodType.ANNUAL, start_date=date(2025, 4, 1), end_date=date(2026, 3, 31))
        self.endpoint = ReportingPeriod.objects.create(name="FY 2030", period_type=PeriodType.ANNUAL, start_date=date(2030, 4, 1), end_date=date(2031, 3, 31))

    def test_independent_goal_kpi_target_and_decreasing_trajectory(self):
        goal = Goal.objects.create(name="Independent goal", created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="energy", name="Energy", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
        target = Target.objects.create(kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("100"), baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("70"), target_unit=self.unit, created_by=self.user)
        middle = ReportingPeriod.objects.create(name="FY 2027", period_type=PeriodType.ANNUAL, start_date=date(2027, 4, 1), end_date=date(2028, 3, 31))
        self.assertEqual(trajectory_value(target, middle), Decimal("88"))
        self.assertEqual(progress_for(target, middle)["status"], "NO_DATA")

    def test_baseline_must_precede_target(self):
        goal = Goal.objects.create(name="Goal", created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="manual", name="Manual", metric_source_type=MetricSourceType.MANUAL_REFERENCE, metric_code="manual", direction=KPIDirection.INCREASE)
        with self.assertRaises(ValidationError):
            Target.objects.create(kpi=kpi, baseline_period=self.endpoint, baseline_value=1, target_period=self.baseline, target_value=2, created_by=self.user)

    def test_session_api_allows_an_independent_goal_and_scopes_target(self):
        permission = Permission.objects.create(code="target.set", name="Set targets", module_code="target", action="EDIT")
        role = Role.objects.create(role_code="targets", role_name="Targets")
        role.permissions.add(permission)
        UserRoleAssignment.objects.create(user=self.user, role=role, org_node=self.org, module_code="target")
        client = APIClient(); client.force_login(self.user)
        response = client.post("/api/targets/goals/", {"name": "No assessment needed", "status": "DRAFT"}, format="json")
        self.assertEqual(response.status_code, 201)
        goal_id = response.data["data"]["id"]
        response = client.post(f"/api/targets/goals/{goal_id}/kpis/", {"code": "manual", "name": "Manual KPI", "metric_source_type": "MANUAL_REFERENCE", "metric_code": "manual.kpi", "direction": "INCREASE", "aggregation": "NONE"}, format="json")
        self.assertEqual(response.status_code, 201)
        response = client.get("/api/targets/goals/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"][0]["name"], "No assessment needed")

    def test_progress_api_uses_annual_periods_and_returns_a_protected_target(self):
        permission = Permission.objects.create(code="target.set", name="Set targets", module_code="target", action="EDIT")
        role = Role.objects.create(role_code="targets-progress", role_name="Targets progress")
        role.permissions.add(permission)
        UserRoleAssignment.objects.create(user=self.user, role=role, org_node=self.org, module_code="target")
        goal = Goal.objects.create(name="Goal", created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="energy-progress", name="Energy", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
        target = Target.objects.create(kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("100"), baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("70"), target_unit=self.unit, created_by=self.user)
        ReportingPeriod.objects.create(parent=self.baseline, name="Apr 2025", period_type=PeriodType.MONTHLY, start_date=date(2025, 4, 1), end_date=date(2025, 4, 30))
        client = APIClient(); client.force_login(self.user)
        response = client.get(f"/api/targets/targets/{target.id}/progress/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all("Apr 2025" != row["name"] for row in response.data["data"]["trajectory"]))

    def test_approved_integer_m5_answers_are_resolved_as_kpi_actuals(self):
        integer_datapoint = Datapoint.objects.create(
            code="waste.generated.test", category=self.category, module=self.module,
            label="Waste", data_type=DatapointDataType.INTEGER,
            unit_family=self.family, default_unit=self.unit,
            collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.ANNUAL,
        )
        request = DataRequest.objects.create(
            datapoint=integer_datapoint, org_node=self.org,
            reporting_period=self.baseline, assignee=self.user, requested_by=self.user,
        )
        submission = Submission.objects.create(data_request=request)
        Answer.objects.create(submission=submission, integer_value=42, unit=self.unit, entered_by=self.user)
        submission.status = SubmissionStatus.APPROVED
        submission._allow_lifecycle_transition = True
        submission.save()
        kpi = KPI.objects.create(
            goal=Goal.objects.create(name="Waste goal", created_by=self.user),
            code="waste", name="Waste", metric_source_type=MetricSourceType.DATAPOINT,
            datapoint=integer_datapoint, direction=KPIDirection.REDUCE,
            aggregation=KPIAggregation.SUM,
        )
        target = Target.objects.create(
            kpi=kpi, org_node=self.org, baseline_period=self.baseline,
            baseline_value=Decimal("50"), baseline_unit=self.unit,
            target_period=self.endpoint, target_value=Decimal("20"),
            target_unit=self.unit, created_by=self.user,
        )
        self.assertEqual(progress_for(target, self.baseline)["actual_value"], Decimal("42"))
