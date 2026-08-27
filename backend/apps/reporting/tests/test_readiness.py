from unittest.mock import patch
from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.reporting.models import ReportRun, SnapshotNode
from apps.reporting.services import ReportReadinessService, freeze_report_run
from apps.frameworks.models import DatapointMapping, FrameworkNode

from .test_services import M8TestDataMixin


class ReportReadinessServiceTests(M8TestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        first = self.make_datapoint("READINESS-AVAILABLE")
        second = self.make_datapoint("READINESS-MISSING")
        third = self.make_datapoint("READINESS-NONE")
        self.make_mapping(node=self.nodes[3], datapoint=first, is_primary=True)
        self.make_mapping(node=self.nodes[3], datapoint=second, is_primary=False)
        self.make_mapping(node=self.nodes[4], datapoint=third, is_primary=True)
        self.run = self.make_report_run()
        freeze_report_run(self.run)
        self.run.refresh_from_db()
        self.snapshot = self.run.framework_snapshot
        self.mappings = list(
            self.snapshot.nodes.get(code="302-1").mappings.order_by("display_order")
        )
        self.missing_mapping = self.snapshot.nodes.get(code="302-2").mappings.get()
        self.unmapped_node = SnapshotNode.objects.create(
            snapshot=self.snapshot,
            code="UNMAPPED",
            title="Unmapped answerable node",
            node_type="DISCLOSURE",
            display_order=3,
            depth=0,
            path="/UNMAPPED/",
            response_format="NUMERIC",
            is_answerable=True,
        )

    def dataset(self):
        available = {
            "snapshot_mapping_id": self.mappings[0].id,
            "status": "RESOLVED",
            "data_type": "DECIMAL",
            "value": 0,
            "unit": None,
            "provenance": {"source_type": "CAPTURED"},
        }
        missing = {
            "snapshot_mapping_id": self.mappings[1].id,
            "status": "UNRESOLVED",
            "data_type": "BOOLEAN",
            "value": False,
            "unit": None,
            "provenance": {"source_type": "CAPTURED"},
        }
        no_value = {
            "snapshot_mapping_id": self.missing_mapping.id,
            "status": "UNRESOLVED",
            "data_type": "TEXT",
            "value": None,
            "unit": None,
            "provenance": {"source_type": "CAPTURED"},
        }
        return [available, missing, no_value]

    @patch("apps.reporting.services.ReportValueResolver.build_dataset")
    def test_explicit_statuses_drive_mapping_and_node_readiness(self, resolver):
        resolver.return_value = self.dataset()

        result = ReportReadinessService.build(self.run)

        self.assertEqual(result["summary"], {
            "frozen_answerable_nodes": 3,
            "mapped_answerable_nodes": 2,
            "unmapped_answerable_nodes": 1,
            "mapping_count": 3,
            "available_mappings": 1,
            "missing_value_mappings": 2,
            "complete_nodes": 0,
            "partial_nodes": 1,
            "missing_nodes": 1,
            "readiness_percentage": 33.33,
        })
        self.assertEqual(
            [node["state"] for node in result["nodes"]],
            ["PARTIAL", "MISSING", "UNMAPPED"],
        )
        self.assertEqual(
            [gap["gap_type"] for gap in result["gaps"]],
            ["MISSING_VALUE", "MISSING_VALUE", "UNMAPPED_NODE"],
        )
        self.assertEqual(result["nodes"][0]["mappings"][0]["state"], "AVAILABLE")
        self.assertEqual(result["nodes"][0]["mappings"][0]["resolved_values"][0]["value"], 0)

    @patch("apps.reporting.services.ReportValueResolver.build_dataset")
    def test_multiple_org_values_are_one_available_mapping(self, resolver):
        resolver.return_value = [
            {
                **self.dataset()[0],
                "value": 100,
                "org_node_id": "plant-a",
            },
            {
                **self.dataset()[0],
                "value": 200,
                "org_node_id": "plant-b",
            },
            self.dataset()[1],
            self.dataset()[2],
        ]

        result = ReportReadinessService.build(self.run)

        self.assertEqual(result["summary"]["available_mappings"], 1)
        self.assertEqual(len(result["nodes"][0]["mappings"][0]["resolved_values"]), 2)

    @patch("apps.reporting.services.ReportValueResolver.build_dataset")
    def test_resolved_boolean_false_is_available(self, resolver):
        resolver.return_value = [{
            **self.dataset()[1],
            "status": "RESOLVED",
            "value": False,
        }]

        result = ReportReadinessService.build(self.run)

        mapping = result["nodes"][0]["mappings"][1]
        self.assertEqual(mapping["state"], "AVAILABLE")
        self.assertEqual(mapping["resolved_values"][0]["value"], False)
        self.assertEqual(result["summary"]["available_mappings"], 1)
        self.assertEqual(result["summary"]["missing_value_mappings"], 2)

    @patch("apps.reporting.services.ReportValueResolver.build_dataset")
    def test_resolved_typed_values_are_preserved_as_available(self, resolver):
        resolver.return_value = [
            {
                **self.dataset()[0],
                "data_type": "TEXT",
                "value": "text value",
                "status": "RESOLVED",
            },
            {
                **self.dataset()[1],
                "data_type": "DATE",
                "value": date(2026, 8, 24),
                "status": "RESOLVED",
            },
            {
                **self.dataset()[2],
                "data_type": "SELECT",
                "value": {"code": "YES", "label": "Yes"},
                "status": "RESOLVED",
            },
        ]

        result = ReportReadinessService.build(self.run)

        mappings = [mapping for node in result["nodes"] for mapping in node["mappings"]]
        self.assertEqual(result["summary"]["available_mappings"], 3)
        self.assertEqual([mapping["state"] for mapping in mappings], ["AVAILABLE"] * 3)
        self.assertEqual(mappings[0]["resolved_values"][0]["value"], "text value")
        self.assertEqual(mappings[1]["resolved_values"][0]["value"], date(2026, 8, 24))
        self.assertEqual(mappings[2]["resolved_values"][0]["value"]["code"], "YES")

    @patch("apps.reporting.services.ReportValueResolver.build_dataset")
    def test_live_m7_edits_do_not_change_frozen_readiness_identity(self, resolver):
        resolver.return_value = self.dataset()
        before = ReportReadinessService.build(self.run)
        live_node = FrameworkNode.objects.get(id=self.nodes[3].id)
        live_mapping = DatapointMapping.objects.get(id=self.mappings[0].source_mapping_id)
        FrameworkNode.objects.filter(id=live_node.id).update(
            code="LIVE-CHANGED",
            title="Changed live title",
        )
        DatapointMapping.objects.filter(id=live_mapping.id).update(
            mapping_note="Changed live mapping",
        )

        after = ReportReadinessService.build(self.run)

        self.assertEqual(after["nodes"], before["nodes"])
        self.assertEqual(after["gaps"], before["gaps"])
        self.assertEqual(after["nodes"][0]["snapshot_node_id"], str(self.snapshot.nodes.get(code="302-1").id))
        self.assertEqual(after["nodes"][0]["mappings"][0]["id"], str(self.mappings[0].id))
        self.assertEqual(
            after["nodes"][0]["mappings"][0]["canonical_datapoint_code"],
            self.mappings[0].canonical_datapoint_code,
        )

    def test_reporting_period_isolation_comes_from_phase_two_resolver(self):
        org_node = self.make_capture_org_node(self.company)
        requester = self.make_capture_user("period-requester")
        maker = self.make_capture_user("period-maker")
        reviewer = self.make_capture_user("period-reviewer")
        first_request = self.make_capture_request(
            datapoint=DatapointMapping.objects.get(id=self.mappings[0].source_mapping_id).datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        )
        self.approve_decimal_submission(
            request=first_request,
            maker=maker,
            reviewer=reviewer,
            value="100",
        )
        second_period = self.make_reporting_period(name="FY 2026-27")
        second_request = self.make_capture_request(
            datapoint=first_request.datapoint,
            org_node=org_node,
            reporting_period=second_period,
            assignee=maker,
            requester=requester,
        )
        self.approve_decimal_submission(
            request=second_request,
            maker=maker,
            reviewer=reviewer,
            value="999",
        )

        result = ReportReadinessService.build(self.run)
        first_mapping = next(
            mapping for node in result["nodes"] for mapping in node["mappings"]
            if mapping["id"] == str(self.mappings[0].id)
        )

        self.assertEqual(first_mapping["state"], "AVAILABLE")
        self.assertEqual(first_mapping["resolved_values"][0]["value"], 100)
        self.assertEqual(len(first_mapping["resolved_values"]), 1)

    @patch("apps.reporting.services.ReportValueResolver.build_dataset", return_value=[])
    def test_readiness_uses_bounded_prefetched_queries(self, resolver):
        with self.assertNumQueries(3):
            ReportReadinessService.build(self.run)

        resolver.assert_called_once_with(self.run)

    def test_readiness_does_not_mutate_m5_m8_or_m7_records(self):
        datapoint = DatapointMapping.objects.get(
            id=self.mappings[0].source_mapping_id,
        ).datapoint
        org_node = self.make_capture_org_node(self.company)
        requester = self.make_capture_user("immutability-requester")
        maker = self.make_capture_user("immutability-maker")
        reviewer = self.make_capture_user("immutability-reviewer")
        request = self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        )
        submission = self.approve_decimal_submission(
            request=request,
            maker=maker,
            reviewer=reviewer,
            value="125",
        )
        answer_before = submission.answer
        submission_status_before = submission.status
        answer_value_before = answer_before.decimal_value
        node_before = SnapshotNode.objects.get(id=self.snapshot.nodes.get(code="302-1").id)
        mapping_before = self.mappings[0]
        live_node_before = FrameworkNode.objects.get(id=self.nodes[3].id)
        live_mapping_before = DatapointMapping.objects.get(id=mapping_before.source_mapping_id)

        ReportReadinessService.build(self.run)

        submission.refresh_from_db()
        answer_before.refresh_from_db()
        node_after = SnapshotNode.objects.get(id=node_before.id)
        mapping_after = type(mapping_before).objects.get(id=mapping_before.id)
        live_node_after = FrameworkNode.objects.get(id=live_node_before.id)
        live_mapping_after = DatapointMapping.objects.get(id=live_mapping_before.id)
        self.assertEqual(submission.status, submission_status_before)
        self.assertEqual(answer_before.decimal_value, answer_value_before)
        self.assertEqual(node_after.code, node_before.code)
        self.assertEqual(mapping_after.canonical_datapoint_code, mapping_before.canonical_datapoint_code)
        self.assertEqual(live_node_after.code, live_node_before.code)
        self.assertEqual(live_mapping_after.mapping_note, live_mapping_before.mapping_note)


class ReportReadinessAPITests(M8TestDataMixin, APITestCase):
    def readiness_url(self, run_id):
        return reverse("report-run-readiness", kwargs={"run_id": run_id})

    def test_unauthenticated_request_is_rejected(self):
        run = self.make_report_run()
        freeze_report_run(run)

        response = self.client.get(self.readiness_url(run.id))

        self.assertIn(response.status_code, {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        })

    def test_unfrozen_request_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        run = self.make_report_run()

        response = self.client.get(self.readiness_url(run.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "The report run has not been frozen yet.")

    @patch("apps.reporting.services.ReportValueResolver.build_dataset", return_value=[])
    def test_authenticated_frozen_request_returns_contract(self, resolver):
        self.client.force_authenticate(user=self.user)
        run = self.make_report_run()
        freeze_report_run(run)

        response = self.client.get(self.readiness_url(run.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["report_run_id"], str(run.id))
        self.assertIsNone(response.data["summary"]["readiness_percentage"])
        resolver.assert_called_once()
