from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.data_capture.models import SubmissionStatus
from apps.reporting.models import ReportRun, SnapshotMapping

from .test_services import M8TestDataMixin


class ResolvedValuesE2ETests(M8TestDataMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.maker = User.objects.create_user(
            username="m8-e2e-maker",
            password="TestPassword123!",
        )
        self.reviewer = User.objects.create_superuser(
            username="m8-e2e-reviewer",
            password="TestPassword123!",
        )
        self.datapoint = self.make_datapoint(code="ENERGY_TOTAL")
        self.make_mapping(datapoint=self.datapoint)
        self.org_node = self.make_capture_org_node(self.company)
        enter_permission = Permission.objects.create(
            code="data.enter",
            name="Enter data",
            module_code="data",
            action="EDIT",
        )
        submit_permission = Permission.objects.create(
            code="data.submit",
            name="Submit data",
            module_code="data",
            action="APPROVE",
        )
        self.maker_role = Role.objects.create(
            role_code="m8-e2e-maker",
            role_name="M8 E2E Maker",
        )
        self.maker_role.permissions.add(enter_permission, submit_permission)
        self.grant_maker_access(self.org_node)

    def grant_maker_access(self, org_node):
        UserRoleAssignment.objects.get_or_create(
            user=self.maker,
            role=self.maker_role,
            org_node=org_node,
            defaults={"module_code": "data"},
        )

    def reporting_url(self, name, **kwargs):
        return reverse(name, kwargs=kwargs)

    def capture_url(self, request_id, suffix):
        return f"/api/data-capture/requests/{request_id}/{suffix}"

    def create_capture_request(self, *, company=None):
        company = company or self.company
        org_node = self.make_capture_org_node(company)
        self.grant_maker_access(org_node)
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            "/api/data-capture/requests/",
            {
                "datapoint": str(self.datapoint.id),
                "org_node": str(org_node.id),
                "reporting_period": str(self.period.id),
                "assignee": str(self.maker.id),
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        return response.data["data"]

    def save_and_submit(self, request_id, value):
        self.client.force_authenticate(user=self.maker)
        answer = self.client.patch(
            self.capture_url(request_id, "submission/answer/"),
            {"decimal_value": str(value)},
            format="json",
        )
        self.assertEqual(answer.status_code, status.HTTP_200_OK)
        submitted = self.client.post(
            self.capture_url(request_id, "submission/submit/"),
            {},
            format="json",
        )
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)

    def approve(self, request_id):
        self.client.force_authenticate(user=self.reviewer)
        approved = self.client.post(
            self.capture_url(request_id, "submission/approve/"),
            {},
            format="json",
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(
            approved.data["data"]["status"],
            SubmissionStatus.APPROVED,
        )

    def create_and_freeze_report(self):
        self.client.force_authenticate(user=self.user)
        created = self.client.post(
            self.reporting_url("report-run-list"),
            {
                "reporting_period": str(self.period.id),
                "framework_version": str(self.framework_version.id),
                "company": str(self.company.id),
                "metadata": {"source": "m8-e2e"},
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        run_id = created.data["id"]
        frozen = self.client.post(
            self.reporting_url("report-run-freeze", run_id=run_id),
            {},
            format="json",
        )
        self.assertEqual(frozen.status_code, status.HTTP_200_OK)
        return ReportRun.objects.get(id=run_id)

    def resolved_values(self, run):
        self.client.force_authenticate(user=self.user)
        return self.client.get(
            self.reporting_url("report-run-resolved-values", run_id=run.id),
        )

    def test_end_to_end_approved_m5_value_resolves_through_m8_api(self):
        request = self.create_capture_request()
        self.save_and_submit(request["id"], Decimal("125.5"))
        self.approve(request["id"])

        run = self.create_and_freeze_report()
        mapping = SnapshotMapping.objects.get(
            snapshot_node__snapshot__report_run=run,
        )
        response = self.resolved_values(run)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ReportRun.Status.FROZEN)
        self.assertEqual(len(response.data["values"]), 1)
        value = response.data["values"][0]
        self.assertEqual(value["status"], "RESOLVED")
        self.assertEqual(Decimal(str(value["value"])), Decimal("125.5"))
        self.assertEqual(value["source_datapoint_id"], self.datapoint.id)
        self.assertEqual(value["canonical_datapoint_code"], "ENERGY_TOTAL")
        self.assertEqual(value["org_node_id"], self.org_node.id)
        self.assertEqual(value["provenance"]["source_type"], "CAPTURED")
        self.assertEqual(mapping.source_datapoint_id, self.datapoint.id)
        self.assertEqual(mapping.canonical_datapoint_code, "ENERGY_TOTAL")

    def test_end_to_end_company_isolation(self):
        company_b = Company.objects.create(
            company_name="M8 E2E Company B",
            company_code="M8E2EB",
            contact_person="M8 Owner B",
            email="m8e2eb@example.com",
            mobile_number="1234567891",
        )
        request_a = self.create_capture_request()
        request_b = self.create_capture_request(company=company_b)
        self.save_and_submit(request_a["id"], Decimal(100))
        self.approve(request_a["id"])
        self.save_and_submit(request_b["id"], Decimal(500))
        self.approve(request_b["id"])

        run = self.create_and_freeze_report()
        response = self.resolved_values(run)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resolved = [item for item in response.data["values"] if item["status"] == "RESOLVED"]
        self.assertEqual(len(resolved), 1)
        self.assertEqual(Decimal(str(resolved[0]["value"])), Decimal(100))
        self.assertNotEqual(resolved[0]["value"], "500")
        self.assertEqual(resolved[0]["org_node_id"], self.org_node.id)

    def test_end_to_end_unapproved_value_is_not_resolved(self):
        request = self.create_capture_request()
        self.save_and_submit(request["id"], Decimal(75))

        run = self.create_and_freeze_report()
        response = self.resolved_values(run)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["values"][0]["status"], "UNRESOLVED")
        self.assertIsNone(response.data["values"][0]["value"])

    def test_end_to_end_unauthenticated_resolved_values_request_is_rejected(self):
        request = self.create_capture_request()
        self.save_and_submit(request["id"], Decimal("125.5"))
        self.approve(request["id"])
        run = self.create_and_freeze_report()

        self.client.force_authenticate(user=None)
        response = self.client.get(
            self.reporting_url("report-run-resolved-values", run_id=run.id),
        )

        self.assertIn(
            response.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )

    def test_end_to_end_missing_value_is_explicitly_unresolved(self):
        run = self.create_and_freeze_report()
        response = self.resolved_values(run)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        value = response.data["values"][0]
        self.assertEqual(value["status"], "UNRESOLVED")
        self.assertIsNone(value["value"])
        self.assertEqual(value["provenance"]["source_type"], "CAPTURED")

    def test_end_to_end_unfrozen_report_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        created = self.client.post(
            self.reporting_url("report-run-list"),
            {
                "reporting_period": str(self.period.id),
                "framework_version": str(self.framework_version.id),
                "company": str(self.company.id),
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        response = self.client.get(
            self.reporting_url(
                "report-run-resolved-values",
                run_id=created.data["id"],
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)