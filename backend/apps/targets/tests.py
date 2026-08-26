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
from apps.materiality.models import AssessmentTopic, MaterialSubTopic, MaterialTopic, MaterialityAssessment, TopicCategory
from apps.core.models import ActivityLog
from apps.targets.models import (
    Goal, KPI, KPIInitiative, KPIDirection, KPIAggregation, MetricSourceType,
    Target, TargetStatus, TargetType,
)
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

    def materiality_context(self):
        topic = MaterialTopic.objects.create(category=TopicCategory.objects.create(code="E", name="Environmental"), name="Water")
        subtopic = MaterialSubTopic.objects.create(topic=topic, code="water-withdrawal", name="Water withdrawal")
        assessment = MaterialityAssessment.objects.create(
            company=self.company, name="Water assessment", reporting_period=self.baseline, created_by=self.user,
        )
        return topic, subtopic, AssessmentTopic.objects.create(assessment=assessment, subtopic=subtopic)

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

    def test_independent_goal_can_later_gain_and_remove_materiality_without_replacing_planning_records(self):
        permission = Permission.objects.create(code="target.set", name="Set targets", module_code="target", action="EDIT")
        role = Role.objects.create(role_code="targets-edit", role_name="Targets edit")
        role.permissions.add(permission)
        UserRoleAssignment.objects.create(user=self.user, role=role, org_node=self.org, module_code="target")
        goal = Goal.objects.create(name="Independent", created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="manual-goal", name="Manual", metric_source_type=MetricSourceType.MANUAL_REFERENCE, metric_code="manual.goal", direction=KPIDirection.INCREASE)
        target = Target.objects.create(kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("1"), target_period=self.endpoint, target_value=Decimal("2"), created_by=self.user)
        topic, subtopic, assessment_topic = self.materiality_context()
        client = APIClient(); client.force_login(self.user)
        response = client.patch(f"/api/targets/goals/{goal.id}/", {"source_assessment_topic": str(assessment_topic.id)}, format="json")
        self.assertEqual(response.status_code, 200)
        goal.refresh_from_db()
        self.assertEqual(goal.material_topic_id, topic.id)
        self.assertEqual(goal.material_subtopic_id, subtopic.id)
        self.assertEqual(goal.source_assessment_topic_id, assessment_topic.id)
        self.assertEqual(goal.kpis.get().id, kpi.id)
        self.assertEqual(kpi.targets.get().id, target.id)
        response = client.patch(f"/api/targets/goals/{goal.id}/", {"material_topic": None, "material_subtopic": None, "source_assessment_topic": None}, format="json")
        self.assertEqual(response.status_code, 200)
        goal.refresh_from_db()
        self.assertIsNone(goal.material_topic)
        self.assertIsNone(goal.material_subtopic)
        self.assertIsNone(goal.source_assessment_topic)
        self.assertEqual(goal.kpis.get().id, kpi.id)
        self.assertEqual(kpi.targets.get().id, target.id)

    def test_rejects_unrelated_subtopic_or_assessment_provenance(self):
        topic, subtopic, assessment_topic = self.materiality_context()
        other_topic = MaterialTopic.objects.create(category=topic.category, name="Energy")
        other_subtopic = MaterialSubTopic.objects.create(topic=other_topic, code="energy-use", name="Energy use")
        goal = Goal.objects.create(name="Goal", created_by=self.user)
        with self.assertRaises(ValidationError):
            Goal.objects.create(name="Invalid subtopic", material_topic=topic, material_subtopic=other_subtopic, created_by=self.user)
        from apps.targets.serializers import GoalWriteSerializer
        serializer = GoalWriteSerializer(goal, data={"material_topic": str(other_topic.id), "material_subtopic": str(other_subtopic.id), "source_assessment_topic": str(assessment_topic.id)}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("source_assessment_topic", serializer.errors)

    def test_initiative_create_edit_status_and_validation(self):
        goal = Goal.objects.create(name="Goal", created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="initiative", name="Initiative KPI", metric_source_type=MetricSourceType.MANUAL_REFERENCE, metric_code="initiative.metric", direction=KPIDirection.INCREASE)
        initiative = KPIInitiative.objects.create(kpi=kpi, name="Install meters", org_node=self.org, owner=self.user, status="PLANNED", due_date=date(2027, 3, 31), anticipated_impact=Decimal("25"))
        initiative.status = "ONGOING"; initiative.description = "Meter programme"
        initiative.save(); initiative.refresh_from_db()
        self.assertEqual(initiative.kpi_id, kpi.id)
        self.assertEqual(initiative.status, "ONGOING")
        with self.assertRaises(ValidationError):
            KPIInitiative.objects.create(kpi=kpi, name="Invalid", anticipated_impact=Decimal("100.01"))
        with self.assertRaises(ValidationError):
            KPIInitiative.objects.create(kpi=kpi, name="Invalid", anticipated_impact=Decimal("-0.01"))

    def test_initiative_api_keeps_the_nested_kpi_context(self):
        permission = Permission.objects.create(code="target.set", name="Set targets", module_code="target", action="EDIT")
        role = Role.objects.create(role_code="targets-initiative", role_name="Targets initiative")
        role.permissions.add(permission)
        UserRoleAssignment.objects.create(user=self.user, role=role, org_node=self.org, module_code="target")
        goal = Goal.objects.create(name="Goal", created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="initiative-api", name="Initiative KPI", metric_source_type=MetricSourceType.MANUAL_REFERENCE, metric_code="initiative.api", direction=KPIDirection.INCREASE)
        other_kpi = KPI.objects.create(goal=goal, code="other-api", name="Other KPI", metric_source_type=MetricSourceType.MANUAL_REFERENCE, metric_code="other.api", direction=KPIDirection.INCREASE)
        client = APIClient(); client.force_login(self.user)
        response = client.post(f"/api/targets/kpis/{kpi.id}/initiatives/", {"name": "Meter programme", "kpi": str(other_kpi.id), "org_node": str(self.org.id), "anticipated_impact": "20"}, format="json")
        self.assertEqual(response.status_code, 201)
        initiative_id = response.data["data"]["id"]
        initiative = KPIInitiative.objects.get(pk=initiative_id)
        self.assertEqual(initiative.kpi_id, kpi.id)
        response = client.patch(f"/api/targets/initiatives/{initiative.id}/", {"kpi": str(other_kpi.id), "status": "ONGOING"}, format="json")
        self.assertEqual(response.status_code, 200)
        initiative.refresh_from_db()
        self.assertEqual(initiative.kpi_id, kpi.id)
        self.assertEqual(initiative.status, "ONGOING")

    def test_metric_source_and_target_contracts_reject_ambiguous_or_invalid_values(self):
        goal = Goal.objects.create(name="Contract goal", created_by=self.user)
        with self.assertRaises(ValidationError):
            KPI.objects.create(
                goal=goal, code="missing-datapoint", name="Missing", metric_source_type=MetricSourceType.DATAPOINT,
                direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM,
            )
        with self.assertRaises(ValidationError):
            KPI.objects.create(
                goal=goal, code="manual-no-code", name="Manual", metric_source_type=MetricSourceType.MANUAL_REFERENCE,
                direction=KPIDirection.REDUCE,
            )
        kpi = KPI.objects.create(
            goal=goal, code="percent", name="Percent", metric_source_type=MetricSourceType.DATAPOINT,
            datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM,
        )
        with self.assertRaises(ValidationError):
            Target.objects.create(
                kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("101"),
                baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("80"), target_unit=self.unit,
                target_type=TargetType.PERCENTAGE, created_by=self.user,
            )
        with self.assertRaises(ValidationError):
            Target.objects.create(
                kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("100"),
                baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("75"), target_unit=self.unit,
                change_percentage=Decimal("-10"), created_by=self.user,
            )
        intensity = Target.objects.create(
            kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("100"),
            baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("75"), target_unit=self.unit,
            target_type=TargetType.INTENSITY, change_percentage=Decimal("-25"), created_by=self.user,
        )
        self.assertEqual(intensity.target_type, TargetType.INTENSITY)

    def test_duplicate_company_wide_active_targets_are_rejected(self):
        kpi = KPI.objects.create(
            goal=Goal.objects.create(name="Duplicate target goal", created_by=self.user), code="duplicate", name="Duplicate",
            metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint,
            direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM,
        )
        kwargs = {
            "kpi": kpi, "baseline_period": self.baseline, "baseline_value": Decimal("100"),
            "baseline_unit": self.unit, "target_period": self.endpoint, "target_value": Decimal("70"),
            "target_unit": self.unit, "created_by": self.user, "status": TargetStatus.ACTIVE,
        }
        Target.objects.create(**kwargs)
        with self.assertRaises(ValidationError):
            Target.objects.create(**kwargs)

    def test_materiality_deletion_nulls_context_without_deleting_planning_records(self):
        topic, subtopic, assessment_topic = self.materiality_context()
        goal = Goal.objects.create(name="Provenance goal", material_topic=topic, material_subtopic=subtopic, source_assessment_topic=assessment_topic, created_by=self.user)
        kpi = KPI.objects.create(goal=goal, code="preserved", name="Preserved", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
        target = Target.objects.create(kpi=kpi, org_node=self.org, baseline_period=self.baseline, baseline_value=Decimal("10"), baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("8"), target_unit=self.unit, created_by=self.user)
        assessment_topic.delete()
        goal.refresh_from_db()
        self.assertIsNone(goal.source_assessment_topic)
        self.assertEqual(goal.kpis.get().id, kpi.id)
        self.assertEqual(kpi.targets.get().id, target.id)


class TargetAuthorizationAcceptanceTests(TestCase):
    """Dedicated M10 D20-style authorization and provider regression matrix."""

    def setUp(self):
        self.owner = User.objects.create_user(username="target-owner", password="safe-password-123")
        self.actor = User.objects.create_user(username="target-scoped", password="safe-password-123")
        self.reader = User.objects.create_user(username="target-reader", password="safe-password-123")
        self.company = Company.objects.create(company_name="Scope Target Co", company_code="TARSCOPE", contact_person="Owner", email="scope@example.test", mobile_number="9999999999")
        self.root = OrgNode.objects.get(company=self.company, node_type="LEGAL_ENTITY")
        self.site_a = OrgNode.objects.create(company=self.company, parent=self.root, node_type="BUSINESS_UNIT", code="TARGET-A", name="Target Site A")
        self.site_a_child = OrgNode.objects.create(company=self.company, parent=self.site_a, node_type="FACILITY", code="TARGET-A-CHILD", name="Target Site A Child")
        self.site_b = OrgNode.objects.create(company=self.company, parent=self.root, node_type="BUSINESS_UNIT", code="TARGET-B", name="Target Site B")
        self.module = Module.objects.create(code="target-test-module", name="Target test module")
        self.category = DatapointCategory.objects.create(code="target-test-category", name="Target category", module=self.module)
        self.family = UnitFamily.objects.create(code="TARGET_TEST_FAMILY", name="Target test family")
        self.unit = Unit.objects.create(family=self.family, code="TARGET_TEST_UNIT", name="Target test unit", factor_to_base=Decimal("1"), is_base_unit=True)
        self.datapoint = Datapoint.objects.create(code="target.scope.decimal", category=self.category, module=self.module, label="Scoped decimal", data_type=DatapointDataType.DECIMAL, unit_family=self.family, default_unit=self.unit, collection_level=CollectionLevel.ORG_NODE, frequency=CollectionFrequency.ANNUAL)
        self.baseline = ReportingPeriod.objects.create(name="Target scope FY 2025", period_type=PeriodType.ANNUAL, start_date=date(2025, 4, 1), end_date=date(2026, 3, 31))
        self.endpoint = ReportingPeriod.objects.create(name="Target scope FY 2030", period_type=PeriodType.ANNUAL, start_date=date(2030, 4, 1), end_date=date(2031, 3, 31))
        self.target_set = Permission.objects.create(code="target.set", name="Set targets", module_code="target", action="EDIT")
        self.target_view = Permission.objects.create(code="target.view", name="View targets", module_code="target", action="VIEW")
        self.other_permission = Permission.objects.create(code="dashboard.view", name="View dashboard", module_code="dashboard", action="VIEW")
        self.setter_role = Role.objects.create(role_code="target-setter-scope", role_name="Target setter scope"); self.setter_role.permissions.add(self.target_set)
        self.reader_role = Role.objects.create(role_code="target-reader-scope", role_name="Target reader scope"); self.reader_role.permissions.add(self.target_view)
        self.other_role = Role.objects.create(role_code="target-other-scope", role_name="Target other scope"); self.other_role.permissions.add(self.other_permission)
        self.goal = Goal.objects.create(name="Scoped planning goal", created_by=self.owner)
        self.kpi = KPI.objects.create(goal=self.goal, code="scoped", name="Scoped KPI", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
        self.target_a = self.make_target(self.site_a)
        self.target_b = self.make_target(self.site_b, target_value=Decimal("60"))

    def grant(self, user, role, node, module="target"):
        return UserRoleAssignment.objects.create(user=user, role=role, org_node=node, module_code=module)

    def make_target(self, org_node, *, target_value=Decimal("70"), status=TargetStatus.ACTIVE):
        return Target.objects.create(kpi=self.kpi, org_node=org_node, baseline_period=self.baseline, baseline_value=Decimal("100"), baseline_unit=self.unit, target_period=self.endpoint, target_value=target_value, target_unit=self.unit, status=status, created_by=self.owner)

    def client_for(self, user):
        client = APIClient(); client.force_login(user); return client

    def test_same_assignment_target_set_scope_does_not_union_with_other_assignment(self):
        self.grant(self.actor, self.setter_role, self.site_a)
        self.grant(self.actor, self.other_role, self.site_b, module="dashboard")
        client = self.client_for(self.actor)
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_a.id}/").status_code, 200)
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_b.id}/").status_code, 404)
        self.assertEqual(client.patch(f"/api/targets/targets/{self.target_b.id}/", {"status": "RETIRED"}, format="json").status_code, 404)
        self.assertEqual(client.get(f"/api/targets/goals/{self.goal.id}/kpis/").status_code, 200)
        ids = {row["id"] for row in client.get(f"/api/targets/kpis/{self.kpi.id}/targets/").data["data"]}
        self.assertEqual(ids, {str(self.target_a.id)})

    def test_target_view_at_site_b_never_expands_target_set_at_site_a(self):
        self.grant(self.actor, self.setter_role, self.site_a)
        self.grant(self.actor, self.reader_role, self.site_b)
        client = self.client_for(self.actor)
        # Read scope legitimately includes Site B through target.view.
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_b.id}/").status_code, 200)
        # Write scope remains only the same qualifying target.set assignment.
        self.assertEqual(client.patch(f"/api/targets/targets/{self.target_b.id}/", {"status": "RETIRED"}, format="json").status_code, 404)

    def test_ancestor_target_set_scope_covers_descendants_but_not_siblings(self):
        self.grant(self.actor, self.setter_role, self.site_a)
        child_target = self.make_target(self.site_a_child, target_value=Decimal("65"))
        client = self.client_for(self.actor)
        self.assertEqual(client.get(f"/api/targets/targets/{child_target.id}/").status_code, 200)
        self.assertEqual(client.patch(f"/api/targets/targets/{child_target.id}/", {"status": "RETIRED"}, format="json").status_code, 200)
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_b.id}/").status_code, 404)

    def test_read_only_target_view_can_read_but_cannot_mutate_or_see_write_controls_contract(self):
        self.grant(self.reader, self.reader_role, self.site_a)
        client = self.client_for(self.reader)
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_a.id}/").status_code, 200)
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_b.id}/").status_code, 404)
        self.assertEqual(client.patch(f"/api/targets/targets/{self.target_a.id}/", {"status": "RETIRED"}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/targets/goals/", {"name": "No write"}, format="json").status_code, 403)

    def test_creator_setup_visibility_expires_once_a_scoped_target_exists(self):
        self.grant(self.actor, self.setter_role, self.site_a)
        setup_goal = Goal.objects.create(name="Actor setup goal", created_by=self.actor)
        setup_kpi = KPI.objects.create(goal=setup_goal, code="setup", name="Setup", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
        client = self.client_for(self.actor)
        self.assertEqual(client.patch(f"/api/targets/goals/{setup_goal.id}/", {"description": "Visible before scope"}, format="json").status_code, 200)
        scoped_target = Target.objects.create(kpi=setup_kpi, org_node=self.site_b, baseline_period=self.baseline, baseline_value=Decimal("100"), baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("80"), target_unit=self.unit, created_by=self.owner)
        self.assertEqual(client.patch(f"/api/targets/goals/{setup_goal.id}/", {"description": "Must not remain writable"}, format="json").status_code, 404)
        self.assertEqual(client.patch(f"/api/targets/targets/{scoped_target.id}/", {"status": "RETIRED"}, format="json").status_code, 404)

    def test_scoped_setter_cannot_create_company_wide_target_or_initiative(self):
        self.grant(self.actor, self.setter_role, self.site_a)
        setup_goal = Goal.objects.create(name="Scoped creator", created_by=self.actor)
        setup_kpi = KPI.objects.create(goal=setup_goal, code="setup-company", name="Setup company", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
        client = self.client_for(self.actor)
        target_payload = {"baseline_period": str(self.baseline.id), "baseline_value": "10", "baseline_unit": str(self.unit.id), "target_period": str(self.endpoint.id), "target_value": "8", "target_unit": str(self.unit.id)}
        self.assertEqual(client.post(f"/api/targets/kpis/{setup_kpi.id}/targets/", target_payload, format="json").status_code, 404)
        self.assertEqual(client.post(f"/api/targets/kpis/{setup_kpi.id}/initiatives/", {"name": "Company planning record"}, format="json").status_code, 404)

    def test_superuser_has_platform_wide_read_and_write_access(self):
        superuser = User.objects.create_superuser(username="target-admin", password="safe-password-123")
        client = self.client_for(superuser)
        self.assertEqual(client.get(f"/api/targets/targets/{self.target_b.id}/").status_code, 200)
        self.assertEqual(client.patch(f"/api/targets/targets/{self.target_b.id}/", {"status": "RETIRED"}, format="json").status_code, 200)

    def test_approved_m5_only_and_progress_direction_statuses_are_deterministic(self):
        kpi = self.kpi
        target = self.target_a
        for value, status, suffix in ((10, SubmissionStatus.DRAFT, "draft"), (20, SubmissionStatus.SUBMITTED, "submitted"), (30, SubmissionStatus.REJECTED, "rejected"), (80, SubmissionStatus.APPROVED, "approved")):
            datapoint = Datapoint.objects.create(code=f"target.answer.{suffix}", category=self.category, module=self.module, label=suffix, data_type=DatapointDataType.DECIMAL, unit_family=self.family, default_unit=self.unit, collection_level=CollectionLevel.ORG_NODE, frequency=CollectionFrequency.ANNUAL)
            request = DataRequest.objects.create(datapoint=datapoint, org_node=self.site_a, reporting_period=self.baseline, assignee=self.owner, requested_by=self.owner)
            submission = Submission.objects.create(data_request=request)
            Answer.objects.create(submission=submission, decimal_value=Decimal(value), unit=self.unit, entered_by=self.owner)
            submission.status = status
            if status == SubmissionStatus.REJECTED:
                submission.rejection_reason = "Deliberately rejected test data."
            submission._allow_lifecycle_transition = True
            submission.save()
            test_kpi = KPI.objects.create(goal=Goal.objects.create(name=f"Goal {suffix}", created_by=self.owner), code=f"kpi-{suffix}", name=suffix, metric_source_type=MetricSourceType.DATAPOINT, datapoint=datapoint, direction=KPIDirection.REDUCE, aggregation=KPIAggregation.SUM)
            test_target = Target.objects.create(kpi=test_kpi, org_node=self.site_a, baseline_period=self.baseline, baseline_value=Decimal("100"), baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("70"), target_unit=self.unit, created_by=self.owner)
            actual = progress_for(test_target, self.baseline)
            if status == SubmissionStatus.APPROVED:
                self.assertEqual(actual["actual_value"], Decimal(value)); self.assertEqual(actual["status"], "AHEAD")
            else:
                self.assertIsNone(actual["actual_value"]); self.assertEqual(actual["status"], "NO_DATA")
        increase_kpi = KPI.objects.create(goal=Goal.objects.create(name="Increase", created_by=self.owner), code="increase", name="Increase", metric_source_type=MetricSourceType.DATAPOINT, datapoint=self.datapoint, direction=KPIDirection.INCREASE, aggregation=KPIAggregation.SUM)
        increase_target = Target.objects.create(kpi=increase_kpi, org_node=self.site_a_child, baseline_period=self.baseline, baseline_value=Decimal("10"), baseline_unit=self.unit, target_period=self.endpoint, target_value=Decimal("20"), target_unit=self.unit, created_by=self.owner)
        request = DataRequest.objects.create(datapoint=self.datapoint, org_node=self.site_a_child, reporting_period=self.baseline, assignee=self.owner, requested_by=self.owner)
        submission = Submission.objects.create(data_request=request); Answer.objects.create(submission=submission, decimal_value=Decimal("12"), unit=self.unit, entered_by=self.owner); submission.status = SubmissionStatus.APPROVED; submission._allow_lifecycle_transition = True; submission.save()
        self.assertEqual(progress_for(increase_target, self.baseline)["status"], "AHEAD")

    def test_target_api_mutations_create_core_activity_logs(self):
        self.grant(self.actor, self.setter_role, self.site_a)
        client = self.client_for(self.actor)
        response = client.post("/api/targets/goals/", {"name": "Audited goal", "status": "DRAFT"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ActivityLog.objects.filter(model_name="Goal", object_id=response.data["data"]["id"], action="CREATE").exists())
