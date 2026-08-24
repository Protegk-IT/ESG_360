from django.test import TestCase

from apps.reporting.models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)
from apps.reporting.serializers import (
    ReportRunSerializer,
    ReportRunDetailSerializer,
    FrameworkSnapshotSerializer,
    SnapshotNodeSerializer,
    SnapshotMappingSerializer,
)

from .test_services import M8TestDataMixin
from apps.reporting.services import freeze_report_run


class ReportRunSerializerTests(M8TestDataMixin, TestCase):

    def test_41_serializer_contains_required_create_fields(self):
        run = self.make_report_run()

        serializer = ReportRunSerializer(
            run,
        )

        self.assertIn(
            "reporting_period",
            serializer.fields,
        )

        self.assertIn(
            "framework_version",
            serializer.fields,
        )

        self.assertIn(
            "metadata",
            serializer.fields,
        )

    def test_42_created_by_is_read_only(self):
        serializer = ReportRunSerializer()

        self.assertTrue(
            serializer.fields[
                "created_by"
            ].read_only
        )

    def test_43_status_is_read_only(self):
        serializer = ReportRunSerializer()

        self.assertTrue(
            serializer.fields[
                "status"
            ].read_only
        )

    def test_44_snapshot_timestamp_is_read_only(self):
        serializer = ReportRunSerializer()

        self.assertTrue(
            serializer.fields[
                "snapshot_frozen_at"
            ].read_only
        )

    def test_45_is_frozen_is_read_only(self):
        serializer = ReportRunSerializer()

        self.assertTrue(
            serializer.fields[
                "is_frozen"
            ].read_only
        )

    def test_46_framework_code_is_exposed(self):
        run = self.make_report_run()

        data = ReportRunSerializer(run).data

        self.assertEqual(
            data["framework_code"],
            "GRI",
        )

    def test_47_framework_version_code_is_exposed(self):
        run = self.make_report_run()

        data = ReportRunSerializer(run).data

        self.assertEqual(
            data["framework_version_code"],
            "GRI-2021",
        )

    def test_48_reporting_period_name_is_exposed(self):
        run = self.make_report_run()

        data = ReportRunSerializer(run).data

        self.assertEqual(
            data["reporting_period_name"],
            self.period.name,
        )


class SnapshotSerializerTests(M8TestDataMixin, TestCase):

    def test_49_snapshot_serializer_exposes_framework_code(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        data = FrameworkSnapshotSerializer(
            snapshot
        ).data

        self.assertEqual(
            data["framework_code"],
            "GRI",
        )

    def test_50_snapshot_serializer_exposes_nodes(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        data = FrameworkSnapshotSerializer(
            snapshot
        ).data

        self.assertEqual(
            len(data["nodes"]),
            len(self.nodes),
        )

    def test_51_snapshot_node_serializer_exposes_parent_code(
        self,
    ):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        child = snapshot.nodes.get(
            code="302-1"
        )

        data = SnapshotNodeSerializer(
            child
        ).data

        self.assertEqual(
            data["parent_code"],
            "GRI-302",
        )

    def test_52_snapshot_mapping_serializer_exposes_canonical_code(
        self,
    ):
        datapoint = self.make_datapoint()

        self.make_mapping(
            datapoint=datapoint,
        )

        run = self.make_report_run()

        freeze_report_run(run)

        mapping = SnapshotMapping.objects.get()

        data = SnapshotMappingSerializer(
            mapping
        ).data

        self.assertEqual(
            data["canonical_datapoint_code"],
            datapoint.code,
        )

    def test_53_snapshot_serializer_does_not_expose_m5_answers(
        self,
    ):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        data = FrameworkSnapshotSerializer(
            snapshot
        ).data

        self.assertNotIn(
            "answers",
            data,
        )

    def test_54_snapshot_serializer_does_not_expose_m6_results(
        self,
    ):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        data = FrameworkSnapshotSerializer(
            snapshot
        ).data

        self.assertNotIn(
            "calculation_results",
            data,
        )