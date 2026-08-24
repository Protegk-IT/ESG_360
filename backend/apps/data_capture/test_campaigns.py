"""Campaign orchestration regressions for Issue #47."""

from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.data_capture.models import CampaignTarget, CollectionCampaignStatus, DataRequest, SubmissionStatus
from apps.data_capture.services.campaigns import CollectionCampaignService
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
)
from apps.modules.models import ESGPillar, Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod, Status as PeriodStatus


class CollectionCampaignServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company_name="Campaign Co", company_code="CAM", contact_person="Owner",
            email="owner@campaign.test", mobile_number="1234567890",
        )
        cls.root = OrgNode.objects.get(
            company=cls.company, node_type="LEGAL_ENTITY", parent__isnull=True
        )
        cls.sites = [
            OrgNode.objects.create(
                company=cls.company, parent=cls.root, node_type="FACILITY",
                code=f"SITE-{number}", name=f"Site {number}",
            )
            for number in range(1, 4)
        ]
        cls.period = ReportingPeriod.objects.create(
            name="Campaign FY 2027", period_type=PeriodType.ANNUAL,
            start_date=date(2027, 4, 1), end_date=date(2028, 3, 31),
        )
        cls.module = Module.objects.create(code="campaign-energy", name="Campaign Energy", esg_pillar=ESGPillar.E)
        cls.category = DatapointCategory.objects.create(
            code="CAMPAIGN", name="Campaign", module=cls.module,
        )
        cls.datapoints = [
            Datapoint.objects.create(
                code=f"CAMPAIGN_{index}", category=cls.category, module=cls.module,
                label=f"Campaign {index}", data_type=DatapointDataType.TEXT,
                collection_level=CollectionLevel.ORG_NODE,
                frequency=CollectionFrequency.ANNUAL,
            )
            for index in range(1, 3)
        ]

        cls.manager = User.objects.create_user(username="campaign-manager", password="pass")
        cls.maker = User.objects.create_user(username="campaign-maker", password="pass")
        cls.reviewer = User.objects.create_user(username="campaign-reviewer", password="pass")
        cls.other_maker = User.objects.create_user(username="campaign-other-maker", password="pass")
        cls.data_manage = Permission.objects.create(
            code="data.manage", name="Manage data", module_code="data", action="MANAGE"
        )
        cls.data_enter = Permission.objects.create(
            code="data.enter", name="Enter data", module_code="data", action="EDIT"
        )
        cls.data_submit = Permission.objects.create(
            code="data.submit", name="Submit data", module_code="data", action="APPROVE"
        )
        cls.data_approve = Permission.objects.create(
            code="data.approve", name="Approve data", module_code="data", action="APPROVE"
        )
        cls.manage_role = Role.objects.create(role_code="campaign-manage", role_name="Campaign manage")
        cls.manage_role.permissions.add(cls.data_manage)
        cls.capture_role = Role.objects.create(role_code="campaign-capture", role_name="Campaign capture")
        cls.capture_role.permissions.add(cls.data_enter, cls.data_submit)
        cls.review_role = Role.objects.create(role_code="campaign-review", role_name="Campaign review")
        cls.review_role.permissions.add(cls.data_approve)
        UserRoleAssignment.objects.create(user=cls.manager, role=cls.manage_role, org_node=cls.root)
        UserRoleAssignment.objects.create(user=cls.maker, role=cls.capture_role, org_node=cls.root)
        UserRoleAssignment.objects.create(user=cls.other_maker, role=cls.capture_role, org_node=cls.root)
        UserRoleAssignment.objects.create(user=cls.reviewer, role=cls.review_role, org_node=cls.root)

    def campaign(self, code="FY27-CAMPAIGN"):
        return CollectionCampaignService.create_campaign(
            actor=self.manager, company=self.company, reporting_period=self.period,
            code=code, name="FY27 Campaign", default_instructions="Capture from source invoice.",
        )

    def cartesian_targets(self, assignee=None):
        return [
            {"datapoint": datapoint, "org_node": site, "assignee": assignee or self.maker}
            for datapoint in self.datapoints for site in self.sites
        ]

    def test_generates_exact_two_by_three_requests_and_derives_module(self):
        campaign = self.campaign()
        targets, summary = CollectionCampaignService.generate_requests(
            campaign, actor=self.manager, targets=self.cartesian_targets()
        )
        self.assertEqual(len(targets), 6)
        self.assertEqual(summary, {"created": 6, "existing": 0, "replayed": 0})
        self.assertEqual(DataRequest.objects.count(), 6)
        self.assertEqual(CampaignTarget.objects.filter(campaign=campaign).count(), 6)
        self.assertEqual(campaign.targets.first().data_request.module_code, self.module.code)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, CollectionCampaignStatus.ACTIVE)

    def test_generation_replay_is_idempotent_and_does_not_duplicate_requests(self):
        campaign = self.campaign()
        CollectionCampaignService.generate_requests(campaign, actor=self.manager, targets=self.cartesian_targets())
        _, summary = CollectionCampaignService.generate_requests(
            campaign, actor=self.manager, targets=self.cartesian_targets()
        )
        self.assertEqual(summary, {"created": 0, "existing": 0, "replayed": 6})
        self.assertEqual(DataRequest.objects.count(), 6)
        self.assertEqual(CampaignTarget.objects.count(), 6)

    def test_existing_equivalent_request_is_linked_without_overwriting_it(self):
        existing = DataCaptureLifecycleService.create_request(
            actor=self.manager, datapoint=self.datapoints[0], org_node=self.sites[0],
            reporting_period=self.period, assignee=self.maker,
            due_date=date(2027, 6, 1), instructions="Existing instruction",
        )
        campaign = self.campaign()
        target = {
            "datapoint": self.datapoints[0], "org_node": self.sites[0],
            "assignee": self.other_maker, "due_date": date(2027, 7, 1),
            "instructions": "New campaign instruction",
        }
        generated, summary = CollectionCampaignService.generate_requests(
            campaign, actor=self.manager, targets=[target]
        )
        self.assertEqual(summary, {"created": 0, "existing": 1, "replayed": 0})
        self.assertEqual(generated[0].data_request_id, existing.id)
        self.assertEqual(generated[0].request_outcome, CampaignTarget.RequestOutcome.EXISTING)
        existing.refresh_from_db()
        self.assertEqual(existing.assignee_id, self.maker.id)
        self.assertEqual(existing.instructions, "Existing instruction")

    def test_invalid_target_prevalidation_rolls_back_the_whole_generation(self):
        campaign = self.campaign()
        self.sites[1].is_active = False
        self.sites[1].save(update_fields=["is_active", "updated_at"])
        with self.assertRaises(ValidationError):
            CollectionCampaignService.generate_requests(
                campaign, actor=self.manager, targets=self.cartesian_targets()
            )
        self.assertFalse(DataRequest.objects.exists())
        self.assertFalse(CampaignTarget.objects.exists())

    def test_collection_level_and_locked_period_are_rejected(self):
        facility_only = Datapoint.objects.create(
            code="CAMPAIGN_FACILITY", category=self.category, module=self.module,
            label="Facility only", data_type=DatapointDataType.TEXT,
            collection_level=CollectionLevel.FACILITY, frequency=CollectionFrequency.ANNUAL,
        )
        campaign = self.campaign()
        with self.assertRaises(ValidationError):
            CollectionCampaignService.generate_requests(campaign, actor=self.manager, targets=[{
                "datapoint": facility_only, "org_node": self.root, "assignee": self.maker,
            }])
        self.period.status = PeriodStatus.LOCKED
        self.period.save(update_fields=["status", "updated_at"])
        with self.assertRaises(ValidationError):
            CollectionCampaignService.generate_requests(campaign, actor=self.manager, targets=[{
                "datapoint": facility_only, "org_node": self.sites[0], "assignee": self.maker,
            }])

    def test_invalid_assignee_and_non_union_manager_scope_are_rejected(self):
        campaign = self.campaign()
        self.other_maker.is_active = False
        self.other_maker.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            CollectionCampaignService.generate_requests(campaign, actor=self.manager, targets=[{
                "datapoint": self.datapoints[0], "org_node": self.sites[0], "assignee": self.other_maker,
            }])

        scoped_manager = User.objects.create_user(username="scoped-manager", password="pass")
        UserRoleAssignment.objects.create(
            user=scoped_manager, role=self.manage_role, org_node=self.sites[0]
        )
        # A different assignment at Site 2 does not move data.manage there.
        UserRoleAssignment.objects.create(
            user=scoped_manager, role=self.capture_role, org_node=self.sites[1]
        )
        with self.assertRaises(PermissionDenied):
            CollectionCampaignService.generate_requests(campaign, actor=scoped_manager, targets=[{
                "datapoint": self.datapoints[0], "org_node": self.sites[1], "assignee": self.maker,
            }])

    def test_bulk_reassignment_is_transactional_and_preserves_request_history(self):
        campaign = self.campaign()
        targets, _ = CollectionCampaignService.generate_requests(
            campaign, actor=self.manager, targets=self.cartesian_targets()
        )
        reassigned = CollectionCampaignService.bulk_reassign(
            campaign, actor=self.manager, target_ids=[target.id for target in targets[:2]],
            assignee=self.other_maker, reason="Regional coverage",
        )
        self.assertEqual(len(reassigned), 2)
        for target in reassigned:
            target.data_request.refresh_from_db()
            self.assertEqual(target.data_request.assignee_id, self.other_maker.id)
            self.assertEqual(target.data_request.events.filter(event_type="REASSIGNED").count(), 1)

    def test_progress_is_derived_from_mixed_request_and_submission_states(self):
        campaign = self.campaign()
        targets, _ = CollectionCampaignService.generate_requests(
            campaign, actor=self.manager, targets=self.cartesian_targets()
        )
        requests = [target.data_request for target in targets]
        DataCaptureLifecycleService.submit(requests[1].submission, actor=self.maker)
        DataCaptureLifecycleService.submit(requests[2].submission, actor=self.maker)
        DataCaptureLifecycleService.approve(requests[2].submission, actor=self.reviewer)
        DataCaptureLifecycleService.submit(requests[3].submission, actor=self.maker)
        DataCaptureLifecycleService.reject(requests[3].submission, actor=self.reviewer, reason="Needs source")
        requests[0].due_date = date.today() - timedelta(days=1)
        requests[0].save(update_fields=["due_date", "updated_at"])

        progress = CollectionCampaignService.progress(campaign.targets.all())
        self.assertEqual(progress["total_targets"], 6)
        self.assertEqual(progress["open_requests"], 5)
        self.assertEqual(progress["completed_requests"], 1)
        self.assertEqual(progress["draft_submissions"], 3)
        self.assertEqual(progress["submitted_submissions"], 1)
        self.assertEqual(progress["approved_submissions"], 1)
        self.assertEqual(progress["rejected_submissions"], 1)
        self.assertEqual(progress["overdue"], 1)


class CollectionCampaignAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            company_name="Campaign API Co", company_code="CAPI", contact_person="Owner",
            email="owner@campaign-api.test", mobile_number="1234567890",
        )
        self.root = OrgNode.objects.get(company=self.company, node_type="LEGAL_ENTITY", parent__isnull=True)
        self.site_a = OrgNode.objects.create(
            company=self.company, parent=self.root, node_type="FACILITY", code="API-A", name="API A"
        )
        self.site_b = OrgNode.objects.create(
            company=self.company, parent=self.root, node_type="FACILITY", code="API-B", name="API B"
        )
        self.period = ReportingPeriod.objects.create(
            name="Campaign API FY", period_type=PeriodType.ANNUAL,
            start_date=date(2028, 4, 1), end_date=date(2029, 3, 31),
        )
        module = Module.objects.create(code="campaign-api", name="Campaign API", esg_pillar=ESGPillar.E)
        category = DatapointCategory.objects.create(code="CAMPAIGN_API", name="Campaign API", module=module)
        self.datapoint = Datapoint.objects.create(
            code="CAMPAIGN_API_TEXT", category=category, module=module, label="Campaign API text",
            data_type=DatapointDataType.TEXT, collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.ANNUAL,
        )
        self.manager = User.objects.create_user(username="campaign-api-manager", password="pass")
        self.limited_manager = User.objects.create_user(username="campaign-api-limited", password="pass")
        self.maker = User.objects.create_user(username="campaign-api-maker", password="pass")
        manage = Permission.objects.create(code="data.manage", name="Manage", module_code="data", action="MANAGE")
        enter = Permission.objects.create(code="data.enter", name="Enter", module_code="data", action="EDIT")
        submit = Permission.objects.create(code="data.submit", name="Submit", module_code="data", action="APPROVE")
        manage_role = Role.objects.create(role_code="campaign-api-manage", role_name="Campaign API manage")
        manage_role.permissions.add(manage)
        capture_role = Role.objects.create(role_code="campaign-api-capture", role_name="Campaign API capture")
        capture_role.permissions.add(enter, submit)
        UserRoleAssignment.objects.create(user=self.manager, role=manage_role, org_node=self.root)
        UserRoleAssignment.objects.create(user=self.limited_manager, role=manage_role, org_node=self.site_a)
        UserRoleAssignment.objects.create(user=self.maker, role=capture_role, org_node=self.root)

    def campaign_payload(self, code="API-FY"):
        return {
            "company": str(self.company.id), "reporting_period": str(self.period.id),
            "code": code, "name": "API campaign", "default_instructions": "Use source records.",
        }

    def target_payload(self, *nodes):
        return {"targets": [{
            "datapoint": str(self.datapoint.id), "org_node": str(node.id), "assignee": self.maker.id,
        } for node in nodes]}

    def test_authenticated_campaign_create_generate_replay_and_progress(self):
        self.client.force_authenticate(self.manager)
        created = self.client.post("/api/data-capture/campaigns/", self.campaign_payload(), format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        campaign_id = created.data["data"]["id"]
        generated = self.client.post(
            f"/api/data-capture/campaigns/{campaign_id}/generate/",
            self.target_payload(self.site_a, self.site_b), format="json",
        )
        self.assertEqual(generated.status_code, status.HTTP_200_OK)
        self.assertEqual(generated.data["data"]["summary"]["created"], 2)
        replay = self.client.post(
            f"/api/data-capture/campaigns/{campaign_id}/generate/",
            self.target_payload(self.site_a, self.site_b), format="json",
        )
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.data["data"]["summary"]["replayed"], 2)
        progress = self.client.get(f"/api/data-capture/campaigns/{campaign_id}/progress/")
        self.assertEqual(progress.status_code, status.HTTP_200_OK)
        self.assertEqual(progress.data["data"]["total_targets"], 2)
        self.assertEqual(progress.data["data"]["draft_submissions"], 2)

    def test_target_scope_is_enforced_and_detail_does_not_leak_other_targets(self):
        campaign = CollectionCampaignService.create_campaign(
            actor=self.manager, company=self.company, reporting_period=self.period,
            code="API-SCOPED", name="Scoped campaign",
        )
        CollectionCampaignService.generate_requests(
            campaign, actor=self.manager, targets=[
                {"datapoint": self.datapoint, "org_node": self.site_a, "assignee": self.maker},
                {"datapoint": self.datapoint, "org_node": self.site_b, "assignee": self.maker},
            ],
        )
        self.client.force_authenticate(self.limited_manager)
        detail = self.client.get(f"/api/data-capture/campaigns/{campaign.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail.data["data"]["targets"]), 1)
        self.assertEqual(detail.data["data"]["events"], [])
        denied = self.client.post(
            f"/api/data-capture/campaigns/{campaign.id}/generate/",
            self.target_payload(self.site_b), format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
