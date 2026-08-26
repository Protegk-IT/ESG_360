from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient

from apps.reporting.models import (
    ReportRun,
    FrameworkSnapshot,
)

from apps.reporting.services import freeze_report_run

from .test_services import M8TestDataMixin


class ReportRunAPITests(M8TestDataMixin, TestCase):

    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )

    def report_runs_url(self):
        return reverse(
            "report-run-list"
        )

    def report_run_detail_url(self, run):
        return reverse(
            "report-run-detail",
            kwargs={
                "pk": run.pk,
            },
        )

    def freeze_url(self, run):
        return reverse(
            "report-run-freeze",
            kwargs={
                "run_id": run.pk,
            },
        )

    def snapshot_url(self, run):
        return reverse(
            "report-run-snapshot",
            kwargs={
                "run_id": run.pk,
            },
        )

    def test_55_authenticated_user_can_list_report_runs(self):
        self.make_report_run()

        response = self.client.get(
            self.report_runs_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_56_authenticated_user_can_create_report_run(
        self,
    ):
        response = self.client.post(
            self.report_runs_url(),
            {
                "reporting_period": str(
                    self.period.pk
                ),
                "framework_version": str(
                    self.framework_version.pk
                ),
                "company": str(self.company.pk),
                "metadata": {
                    "source": "api-test"
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            ReportRun.objects.count(),
            1,
        )

    def test_57_create_report_run_defaults_to_draft(self):
        response = self.client.post(
            self.report_runs_url(),
            {
                "reporting_period": str(
                    self.period.pk
                ),
                "framework_version": str(
                    self.framework_version.pk
                ),
                "company": str(self.company.pk),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        run = ReportRun.objects.get()

        self.assertEqual(
            run.status,
            ReportRun.Status.DRAFT,
        )

    def test_58_create_report_run_sets_authenticated_user(
        self,
    ):
        response = self.client.post(
            self.report_runs_url(),
            {
                "reporting_period": str(
                    self.period.pk
                ),
                "framework_version": str(
                    self.framework_version.pk
                ),
                "company": str(self.company.pk),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        run = ReportRun.objects.get()

        self.assertEqual(
            run.created_by_id,
            self.user.pk,
        )

    def test_59_invalid_reporting_period_is_rejected(self):
        import uuid

        response = self.client.post(
            self.report_runs_url(),
            {
                "reporting_period": str(
                    uuid.uuid4()
                ),
                "framework_version": str(
                    self.framework_version.pk
                ),
                "company": str(self.company.pk),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            [400, 404],
        )

        self.assertEqual(
            ReportRun.objects.count(),
            0,
        )

    def test_60_invalid_framework_version_is_rejected(self):
        import uuid

        response = self.client.post(
            self.report_runs_url(),
            {
                "reporting_period": str(
                    self.period.pk
                ),
                "framework_version": str(
                    uuid.uuid4()
                ),
                "company": str(self.company.pk),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            [400, 404],
        )

        self.assertEqual(
            ReportRun.objects.count(),
            0,
        )

    def test_61_detail_endpoint_returns_run(self):
        run = self.make_report_run()

        response = self.client.get(
            self.report_run_detail_url(run)
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(run.pk),
        )

    def test_62_freeze_endpoint_freezes_run(self):
        run = self.make_report_run()

        response = self.client.post(
            self.freeze_url(run)
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        run.refresh_from_db()

        self.assertTrue(
            run.is_frozen,
        )

    def test_63_freeze_endpoint_creates_snapshot(self):
        run = self.make_report_run()

        response = self.client.post(
            self.freeze_url(run)
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            FrameworkSnapshot.objects.filter(
                report_run=run
            ).exists()
        )

    def test_64_second_freeze_is_rejected(self):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.post(
            self.freeze_url(run)
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_65_snapshot_endpoint_requires_frozen_run(self):
        run = self.make_report_run()

        response = self.client.get(
            self.snapshot_url(run)
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_66_snapshot_endpoint_returns_snapshot(self):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.get(
            self.snapshot_url(run)
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["report_run_id"],
            str(run.pk),
        )

    def test_67_snapshot_endpoint_returns_nodes(self):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.get(
            self.snapshot_url(run)
        )

        self.assertEqual(
            len(response.data["nodes"]),
            len(self.nodes),
        )

    def test_68_snapshot_endpoint_returns_mapping(
        self,
    ):
        datapoint = self.make_datapoint()

        self.make_mapping(
            datapoint=datapoint,
        )

        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.get(
            self.snapshot_url(run)
        )

        answerable_node = next(
            node
            for node in response.data["nodes"]
            if node["code"] == "302-1"
        )

        self.assertEqual(
            len(answerable_node["mappings"]),
            1,
        )

        self.assertEqual(
            answerable_node["mappings"][0][
                "canonical_datapoint_code"
            ],
            datapoint.code,
        )

    def test_69_patch_frozen_run_is_rejected(self):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.patch(
            self.report_run_detail_url(run),
            {
                "metadata": {
                    "changed": True
                }
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_70_delete_frozen_run_is_rejected(self):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.delete(
            self.report_run_detail_url(run)
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_71_snapshot_endpoint_is_read_only(self):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        response = self.client.post(
            self.snapshot_url(run),
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [405, 403],
        )

    def test_72_live_m7_edit_does_not_change_api_snapshot(
        self,
    ):
        run = self.make_report_run()

        self.client.post(
            self.freeze_url(run)
        )

        before = self.client.get(
            self.snapshot_url(run)
        )

        self.nodes[3].title = (
            "MODIFIED AFTER FREEZE"
        )
        self.nodes[3].save()

        after = self.client.get(
            self.snapshot_url(run)
        )

        before_node = next(
            node
            for node in before.data["nodes"]
            if node["code"] == "302-1"
        )

        after_node = next(
            node
            for node in after.data["nodes"]
            if node["code"] == "302-1"
        )

        self.assertEqual(
            before_node["title"],
            "Energy consumption",
        )

        self.assertEqual(
            after_node["title"],
            "Energy consumption",
        )

    def test_73_unauthenticated_run_list_is_rejected(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            self.report_runs_url()
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_74_unauthenticated_snapshot_is_rejected(self):
        run = self.make_report_run()

        freeze_report_run(run)

        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            self.snapshot_url(run)
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )
