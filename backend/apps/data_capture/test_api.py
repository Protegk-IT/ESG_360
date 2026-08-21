from datetime import date
from decimal import Decimal
import os
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.data_capture.models import EvidenceFile, SubmissionStatus
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.data_capture.services.evidence import EvidenceService
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    DatapointTableColumn,
    DatapointTableRow,
    Unit,
    UnitFamily,
)
from apps.modules.models import ESGPillar, Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod, Status as PeriodStatus


class DataCaptureAPITests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="m5-evidence-")
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.company = Company.objects.create(
            company_name="M5 API Co", company_code="M5API", contact_person="Owner",
            email="owner@m5.test", mobile_number="1234567890",
        )
        self.root = OrgNode.objects.get(company=self.company, parent__isnull=True)
        self.site_a = OrgNode.objects.create(
            company=self.company, parent=self.root, node_type="FACILITY", code="M5-A", name="M5 Site A"
        )
        self.site_b = OrgNode.objects.create(
            company=self.company, parent=self.root, node_type="FACILITY", code="M5-B", name="M5 Site B"
        )
        self.period = ReportingPeriod.objects.create(
            name="FY 2027", period_type=PeriodType.ANNUAL,
            start_date=date(2027, 4, 1), end_date=date(2028, 3, 31),
        )
        self.module = Module.objects.create(code="energy", name="Energy", esg_pillar=ESGPillar.E)
        self.category = DatapointCategory.objects.create(
            code="M5_API", name="M5 API", module=self.module
        )
        self.family = UnitFamily.objects.create(code="M5_ENERGY", name="M5 Energy")
        self.unit = Unit.objects.create(
            family=self.family, code="M5_KWH", name="M5 kWh", factor_to_base=Decimal("1"), is_base_unit=True
        )
        self.decimal_datapoint = Datapoint.objects.create(
            code="M5_API_DECIMAL", category=self.category, module=self.module,
            label="API decimal", data_type=DatapointDataType.DECIMAL,
            unit_family=self.family, default_unit=self.unit, is_required=True,
            collection_level=CollectionLevel.ORG_NODE, frequency=CollectionFrequency.MONTHLY,
            validation_metadata={"min": "0"},
        )
        self.table_datapoint = Datapoint.objects.create(
            code="M5_API_TABLE", category=self.category, module=self.module,
            label="API table", data_type=DatapointDataType.TABLE, is_required=True,
            collection_level=CollectionLevel.ORG_NODE, frequency=CollectionFrequency.MONTHLY,
        )
        self.table_column = DatapointTableColumn.objects.create(
            datapoint=self.table_datapoint, code="SOURCE", label="Source",
            data_type=DatapointDataType.TEXT, is_required=True, display_order=1,
        )
        self.table_row = DatapointTableRow.objects.create(
            datapoint=self.table_datapoint, code="GRID", label="Grid", display_order=1
        )

        self.manager = self.user("manager")
        self.maker = self.user("maker")
        self.reviewer_a = self.user("reviewer-a")
        self.reviewer_b = self.user("reviewer-b")
        self.other = self.user("other")
        self.capture_a = self.user("capture-a")
        self.superuser = User.objects.create_superuser(username="m5-admin", password="safe-password-123")

        self.data_manage = self.permission("data.manage", "MANAGE")
        self.data_enter = self.permission("data.enter", "EDIT")
        self.data_submit = self.permission("data.submit", "APPROVE")
        self.data_approve = self.permission("data.approve", "APPROVE")
        self.evidence_upload = self.permission("evidence.upload", "CREATE", module_code="evidence")
        self.evidence_view = self.permission("evidence.view", "VIEW", module_code="evidence")
        self.manage_role = self.role("m5-manager", self.data_manage)
        self.entry_role = self.role(
            "m5-entry", self.data_enter, self.data_submit, self.evidence_upload, self.evidence_view
        )
        self.approve_role = self.role("m5-approve", self.data_approve, self.evidence_view)

        UserRoleAssignment.objects.create(user=self.manager, role=self.manage_role, org_node=self.site_a)
        UserRoleAssignment.objects.create(user=self.maker, role=self.entry_role, org_node=self.site_a)
        UserRoleAssignment.objects.create(user=self.reviewer_a, role=self.approve_role, org_node=self.site_a)
        UserRoleAssignment.objects.create(user=self.reviewer_b, role=self.approve_role, org_node=self.site_b)
        UserRoleAssignment.objects.create(user=self.other, role=self.entry_role, org_node=self.site_b)
        UserRoleAssignment.objects.create(user=self.capture_a, role=self.entry_role, org_node=self.site_a)

        self.request_a = self.create_request(self.decimal_datapoint, self.site_a, self.maker)
        self.request_b = self.create_request(self.decimal_datapoint, self.site_b, self.other)
        self.table_request = self.create_request(self.table_datapoint, self.site_a, self.maker)

    @staticmethod
    def user(username):
        return User.objects.create_user(username=username, password="safe-password-123")

    @staticmethod
    def permission(code, action, module_code="data"):
        return Permission.objects.create(code=code, name=code, module_code=module_code, action=action)

    @staticmethod
    def role(code, *permissions):
        role = Role.objects.create(role_code=code, role_name=code)
        role.permissions.add(*permissions)
        return role

    def create_request(self, datapoint, org_node, assignee):
        return DataCaptureLifecycleService.create_request(
            actor=self.superuser,
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=assignee,
        )

    def additional_datapoint(self, code):
        return Datapoint.objects.create(
            code=code, category=self.category, module=self.module, label=code,
            data_type=DatapointDataType.TEXT, collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.MONTHLY,
        )

    def login(self, user):
        self.client.force_authenticate(user=user)

    def path(self, request, suffix=""):
        return f"/api/data-capture/requests/{request.id}/{suffix}"

    def evidence_path(self, request, evidence_id=None, suffix=""):
        path = self.path(request, "evidence/")
        if evidence_id:
            path = f"{path}{evidence_id}/"
        return f"{path}{suffix}"

    def save_decimal(self, request=None):
        request = request or self.request_a
        return self.client.patch(
            self.path(request, "submission/answer/"), {"decimal_value": "12.50"}, format="json"
        )

    @staticmethod
    def pdf_file(name="invoice.pdf", content_type="application/pdf", body=b"%PDF-1.4\ninvoice"):
        return SimpleUploadedFile(name, body, content_type=content_type)

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get("/api/data-capture/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])

    def test_assigned_capture_user_sees_only_own_scoped_requests_and_mine(self):
        self.login(self.maker)
        response = self.client.get("/api/data-capture/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data["data"]["results"]},
            {str(self.request_a.id), str(self.table_request.id)},
        )
        mine = self.client.get("/api/data-capture/requests/mine/")
        self.assertEqual(mine.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mine.data["data"]["results"]), 2)
        detail = self.client.get(self.path(self.request_a))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        submission = self.client.get(self.path(self.request_a, "submission/"))
        self.assertEqual(submission.status_code, status.HTTP_200_OK)
        self.assertEqual(submission.data["data"]["status"], SubmissionStatus.DRAFT)

    def test_permission_and_scope_do_not_union_between_role_assignments(self):
        """`enter` at A plus `approve` at B never permits approval at A."""
        UserRoleAssignment.objects.create(user=self.maker, role=self.approve_role, org_node=self.site_b)
        self.login(self.maker)

        readable = self.client.get("/api/data-capture/requests/")
        self.assertEqual(readable.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in readable.data["data"]["results"]},
            {str(self.request_a.id), str(self.table_request.id), str(self.request_b.id)},
        )
        out_of_scope_action = self.client.post(self.path(self.request_a, "submission/approve/"), {}, format="json")
        self.assertEqual(out_of_scope_action.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(out_of_scope_action.data["success"])

    def test_out_of_scope_detail_is_hidden(self):
        self.login(self.maker)
        response = self.client.get(self.path(self.request_b))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])

    def test_data_manage_can_create_and_reassign_only_inside_scope(self):
        self.login(self.manager)
        datapoint = self.additional_datapoint("M5_API_CREATE")
        valid = self.client.post("/api/data-capture/requests/", {
            "datapoint": str(datapoint.id), "org_node": str(self.site_a.id),
            "reporting_period": str(self.period.id), "assignee": str(self.capture_a.id),
        }, format="json")
        self.assertEqual(valid.status_code, status.HTTP_201_CREATED)
        duplicate = self.client.post("/api/data-capture/requests/", {
            "datapoint": str(datapoint.id), "org_node": str(self.site_a.id),
            "reporting_period": str(self.period.id), "assignee": str(self.capture_a.id),
        }, format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("__all__", duplicate.data["errors"])
        out_of_scope = self.client.post("/api/data-capture/requests/", {
            "datapoint": str(datapoint.id), "org_node": str(self.site_b.id),
            "reporting_period": str(self.period.id), "assignee": str(self.capture_a.id),
        }, format="json")
        self.assertEqual(out_of_scope.status_code, status.HTTP_404_NOT_FOUND)
        ineligible_assignee = self.client.post("/api/data-capture/requests/", {
            "datapoint": str(self.additional_datapoint("M5_API_INELIGIBLE").id),
            "org_node": str(self.site_a.id), "reporting_period": str(self.period.id),
            # This user can capture Site B, but not Site A.
            "assignee": str(self.other.id),
        }, format="json")
        self.assertEqual(ineligible_assignee.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assignee", ineligible_assignee.data["errors"])
        reassign = self.client.post(self.path(self.request_a, "reassign/"), {
            "assignee": str(self.capture_a.id), "reason": "Coverage",
        }, format="json")
        self.assertEqual(reassign.status_code, status.HTTP_200_OK)
        self.request_a.refresh_from_db()
        self.assertEqual(self.request_a.assignee, self.capture_a)

    def test_maker_only_write_endpoints_hide_another_assignees_request(self):
        DataCaptureLifecycleService.reassign_request(
            self.request_a, actor=self.manager, assignee=self.capture_a
        )
        self.login(self.maker)
        answer = self.client.patch(
            self.path(self.request_a, "submission/answer/"), {"decimal_value": "1"}, format="json"
        )
        self.assertEqual(answer.status_code, status.HTTP_404_NOT_FOUND)
        submit = self.client.post(self.path(self.request_a, "submission/submit/"), {}, format="json")
        self.assertEqual(submit.status_code, status.HTTP_404_NOT_FOUND)
        evidence = self.client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file()}, format="multipart"
        )
        self.assertEqual(evidence.status_code, status.HTTP_404_NOT_FOUND)

    def test_scalar_draft_save_uses_domain_validation_and_rejects_status_mutation(self):
        self.login(self.maker)
        saved = self.save_decimal()
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        self.assertEqual(str(saved.data["data"]["answer"]["unit"]), str(self.unit.id))
        invalid = self.client.patch(
            self.path(self.request_a, "submission/answer/"), {"text_value": "wrong type"}, format="json"
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("datapoint", invalid.data["errors"])
        direct_status = self.client.patch(
            self.path(self.request_a, "submission/answer/"),
            {"decimal_value": "13", "status": "APPROVED"}, format="json",
        )
        self.assertEqual(direct_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.request_a.submission.refresh_from_db()
        self.assertEqual(self.request_a.submission.status, SubmissionStatus.DRAFT)

    def test_table_draft_save_and_row_update_are_normalized(self):
        self.login(self.maker)
        created = self.client.post(self.path(self.table_request, "submission/table-rows/"), {
            "definition_row": str(self.table_row.id), "display_order": 99,
            "cells": [{"column": str(self.table_column.id), "text_value": "Grid power"}],
        }, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        row = created.data["data"]["answer"]["table_rows"][0]
        self.assertEqual(row["display_order"], 1)
        updated = self.client.patch(
            self.path(self.table_request, f"submission/table-rows/{row['id']}/"),
            {"cells": [{"column": str(self.table_column.id), "text_value": "Updated grid power"}]},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["data"]["answer"]["table_rows"][0]["cells"][0]["text_value"], "Updated grid power")

    def test_submit_approve_reject_reopen_and_history_actions_use_lifecycle(self):
        self.login(self.maker)
        self.assertEqual(self.save_decimal().status_code, status.HTTP_200_OK)
        submitted = self.client.post(self.path(self.request_a, "submission/submit/"), {}, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)

        # The submitter cannot self-approve even after receiving the capability.
        UserRoleAssignment.objects.create(user=self.maker, role=self.approve_role, org_node=self.site_a)
        self.client.force_authenticate(user=self.maker)
        self.assertEqual(
            self.client.post(self.path(self.request_a, "submission/approve/"), {}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                self.path(self.request_a, "submission/reject/"), {"reason": "self review"}, format="json"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(user=self.reviewer_a)
        rejected_without_reason = self.client.post(self.path(self.request_a, "submission/reject/"), {"reason": ""}, format="json")
        self.assertEqual(rejected_without_reason.status_code, status.HTTP_400_BAD_REQUEST)
        rejected = self.client.post(self.path(self.request_a, "submission/reject/"), {"reason": "Need evidence"}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        reopened_without_reason = self.client.post(self.path(self.request_a, "submission/reopen/"), {"reason": ""}, format="json")
        self.assertEqual(reopened_without_reason.status_code, status.HTTP_400_BAD_REQUEST)
        reopened = self.client.post(self.path(self.request_a, "submission/reopen/"), {"reason": "Correct and resubmit"}, format="json")
        self.assertEqual(reopened.status_code, status.HTTP_200_OK)
        history = self.client.get(self.path(self.request_a, "submission/history/"))
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["event_type"] for item in history.data["data"]["submission_events"]],
            ["CREATED", "DRAFT_SAVED", "SUBMITTED", "REJECTED", "REOPENED"],
        )

    def test_reviewer_can_approve_a_submitted_request(self):
        self.login(self.maker)
        self.assertEqual(self.save_decimal().status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(self.path(self.request_a, "submission/submit/"), {}, format="json").status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=self.reviewer_a)
        approved = self.client.post(self.path(self.request_a, "submission/approve/"), {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data["data"]["status"], SubmissionStatus.APPROVED)

    def test_locked_period_and_superuser_behavior_are_preserved(self):
        self.period.status = PeriodStatus.LOCKED
        self.period.save()
        self.login(self.maker)
        locked = self.save_decimal()
        self.assertEqual(locked.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.superuser)
        all_requests = self.client.get("/api/data-capture/requests/")
        self.assertEqual(all_requests.status_code, status.HTTP_200_OK)
        self.assertEqual(len(all_requests.data["data"]["results"]), 3)

    def test_evidence_upload_uses_server_metadata_and_supports_answer_linking(self):
        self.login(self.maker)
        answer_id = self.save_decimal().data["data"]["answer"]["id"]
        response = self.client.post(
            self.evidence_path(self.request_a),
            {
                "file": self.pdf_file("utility.pdf", "text/plain"),
                "answer": answer_id,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        evidence_data = response.data["data"]
        self.assertEqual(evidence_data["original_filename"], "utility.pdf")
        self.assertEqual(evidence_data["content_type"], "application/pdf")
        self.assertEqual(evidence_data["size"], len(b"%PDF-1.4\ninvoice"))
        self.assertEqual(str(evidence_data["answer"]), str(answer_id))
        self.assertNotIn("file", evidence_data)

        listed = self.client.get(self.evidence_path(self.request_a))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data["data"]["results"]), 1)
        detail = self.client.get(self.evidence_path(self.request_a, evidence_data["id"]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

    def test_unauthenticated_evidence_access_is_rejected(self):
        response = self.client.get(self.evidence_path(self.request_a))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])

    def test_evidence_rejects_invalid_type_oversize_and_cross_submission_answer(self):
        self.login(self.maker)
        invalid = self.client.post(
            self.evidence_path(self.request_a),
            {"file": self.pdf_file("not-a-pdf.pdf", body=b"MZ executable")},
            format="multipart",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", invalid.data["errors"])
        oversized = self.client.post(
            self.evidence_path(self.request_a),
            {"file": self.pdf_file(body=b"%PDF-" + b"x" * (EvidenceFile.MAX_FILE_SIZE + 1))},
            format="multipart",
        )
        self.assertEqual(oversized.status_code, status.HTTP_400_BAD_REQUEST)

        table = self.client.post(self.path(self.table_request, "submission/table-rows/"), {
            "definition_row": str(self.table_row.id), "display_order": 1,
            "cells": [{"column": str(self.table_column.id), "text_value": "Grid"}],
        }, format="json")
        foreign_answer_id = table.data["data"]["answer"]["id"]
        cross_submission = self.client.post(
            self.evidence_path(self.request_a),
            {"file": self.pdf_file(), "answer": foreign_answer_id},
            format="multipart",
        )
        self.assertEqual(cross_submission.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("answer", cross_submission.data["errors"])

    def test_evidence_scope_download_and_safe_storage_deletion(self):
        self.login(self.maker)
        uploaded = self.client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file()}, format="multipart"
        )
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED)
        evidence_id = uploaded.data["data"]["id"]
        evidence = EvidenceFile.objects.get(pk=evidence_id)
        stored_name = evidence.file.name
        self.assertTrue(default_storage.exists(stored_name))

        download = self.client.get(self.evidence_path(self.request_a, evidence_id, "download/"))
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(download.streaming_content), b"%PDF-1.4\ninvoice")
        self.assertIn("invoice.pdf", download["Content-Disposition"])

        self.client.force_authenticate(user=self.reviewer_b)
        out_of_scope = self.client.get(self.evidence_path(self.request_a, evidence_id, "download/"))
        self.assertEqual(out_of_scope.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(out_of_scope.data["success"])

        self.client.force_authenticate(user=self.maker)
        with self.captureOnCommitCallbacks(execute=True):
            deleted = self.client.delete(self.evidence_path(self.request_a, evidence_id))
        self.assertEqual(deleted.status_code, status.HTTP_200_OK)
        self.assertFalse(EvidenceFile.objects.filter(pk=evidence_id).exists())
        self.assertFalse(default_storage.exists(stored_name))

    def test_failed_evidence_persistence_cleans_up_filefield_storage(self):
        self.login(self.maker)
        with patch("apps.core.mixins.ActivityLog.objects.create", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                EvidenceService.upload(
                    self.request_a.submission,
                    actor=self.maker,
                    uploaded_file=self.pdf_file("failed.pdf"),
                )
        self.assertEqual(
            [name for _, _, files in os.walk(self.media_root) for name in files],
            [],
        )

    def test_evidence_deletion_and_upload_are_blocked_outside_editable_draft(self):
        self.login(self.maker)
        self.assertEqual(self.save_decimal().status_code, status.HTTP_200_OK)
        uploaded = self.client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file()}, format="multipart"
        )
        evidence_id = uploaded.data["data"]["id"]
        self.assertEqual(
            self.client.post(self.path(self.request_a, "submission/submit/"), {}, format="json").status_code,
            status.HTTP_200_OK,
        )
        deletion = self.client.delete(self.evidence_path(self.request_a, evidence_id))
        self.assertEqual(deletion.status_code, status.HTTP_400_BAD_REQUEST)
        second_upload = self.client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file("after-submit.pdf")}, format="multipart"
        )
        self.assertEqual(second_upload.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(EvidenceFile.objects.filter(pk=evidence_id).exists())

    def test_locked_period_blocks_evidence_upload(self):
        self.period.status = PeriodStatus.LOCKED
        self.period.save()
        self.login(self.maker)
        response = self.client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file()}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_evidence_upload_requires_csrf_for_session_authenticated_user(self):
        client = Client(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="maker", password="safe-password-123"))
        without_token = client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file()},
        )
        self.assertEqual(without_token.status_code, status.HTTP_403_FORBIDDEN)
        token = client.get("/api/accounts/csrf/").json()["csrfToken"]
        with_token = client.post(
            self.evidence_path(self.request_a), {"file": self.pdf_file()}, HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(with_token.status_code, status.HTTP_201_CREATED)

    def test_m5_vertical_slice_uses_scoped_api_domain_and_durable_history(self):
        """Representative M4 → M5 flow without using superuser for capture/review."""
        scalar = self.additional_datapoint("M5_VERTICAL_SCALAR")
        table = Datapoint.objects.create(
            code="M5_VERTICAL_TABLE", category=self.category, module=self.module,
            label="Vertical table", data_type=DatapointDataType.TABLE, is_required=True,
            collection_level=CollectionLevel.ORG_NODE, frequency=CollectionFrequency.MONTHLY,
        )
        table_column = DatapointTableColumn.objects.create(
            datapoint=table, code="SOURCE", label="Source", data_type=DatapointDataType.TEXT,
            is_required=True, display_order=1,
        )
        fixed_row = DatapointTableRow.objects.create(
            datapoint=table, code="GRID", label="Grid", display_order=1
        )

        self.login(self.manager)
        created_scalar = self.client.post("/api/data-capture/requests/", {
            "datapoint": str(scalar.id), "org_node": str(self.site_a.id),
            "reporting_period": str(self.period.id), "assignee": str(self.maker.id),
        }, format="json")
        created_table = self.client.post("/api/data-capture/requests/", {
            "datapoint": str(table.id), "org_node": str(self.site_a.id),
            "reporting_period": str(self.period.id), "assignee": str(self.maker.id),
        }, format="json")
        self.assertEqual(created_scalar.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created_table.status_code, status.HTTP_201_CREATED)
        scalar_id = created_scalar.data["data"]["id"]
        table_id = created_table.data["data"]["id"]

        self.client.force_authenticate(user=self.maker)
        self.assertEqual(self.client.get(f"/api/data-capture/requests/{scalar_id}/").status_code, status.HTTP_200_OK)
        draft = self.client.patch(
            f"/api/data-capture/requests/{scalar_id}/submission/answer/", {"text_value": "Metered total"}, format="json"
        )
        self.assertEqual(draft.status_code, status.HTTP_200_OK)
        table_draft = self.client.post(
            f"/api/data-capture/requests/{table_id}/submission/table-rows/", {
                "definition_row": str(fixed_row.id), "display_order": 1,
                "cells": [{"column": str(table_column.id), "text_value": "Grid"}],
            }, format="json",
        )
        self.assertEqual(table_draft.status_code, status.HTTP_201_CREATED)
        evidence = self.client.post(
            f"/api/data-capture/requests/{scalar_id}/evidence/", {"file": self.pdf_file()}, format="multipart"
        )
        self.assertEqual(evidence.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.get(f"/api/data-capture/requests/{scalar_id}/submission/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f"/api/data-capture/requests/{scalar_id}/evidence/").status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(f"/api/data-capture/requests/{scalar_id}/submission/submit/", {}, format="json").status_code,
            status.HTTP_200_OK,
        )

        self.client.force_authenticate(user=self.reviewer_a)
        self.assertEqual(
            self.client.post(
                f"/api/data-capture/requests/{scalar_id}/submission/reject/", {"reason": "Clarify source."}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                f"/api/data-capture/requests/{scalar_id}/submission/reopen/", {"reason": "Corrected."}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=self.maker)
        self.assertEqual(
            self.client.post(f"/api/data-capture/requests/{scalar_id}/submission/submit/", {}, format="json").status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=self.reviewer_a)
        self.assertEqual(
            self.client.post(f"/api/data-capture/requests/{scalar_id}/submission/approve/", {}, format="json").status_code,
            status.HTTP_200_OK,
        )
        history = self.client.get(f"/api/data-capture/requests/{scalar_id}/submission/history/")
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [event["event_type"] for event in history.data["data"]["submission_events"]],
            ["CREATED", "DRAFT_SAVED", "SUBMITTED", "REJECTED", "REOPENED", "SUBMITTED", "APPROVED"],
        )

    def test_session_authenticated_unsafe_requests_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="maker", password="safe-password-123"))
        without_token = client.patch(
            self.path(self.request_a, "submission/answer/"),
            data='{"decimal_value":"5"}', content_type="application/json",
        )
        self.assertEqual(without_token.status_code, status.HTTP_403_FORBIDDEN)
        token = client.get("/api/accounts/csrf/").json()["csrfToken"]
        with_token = client.patch(
            self.path(self.request_a, "submission/answer/"),
            data='{"decimal_value":"5"}', content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(with_token.status_code, status.HTTP_200_OK)
