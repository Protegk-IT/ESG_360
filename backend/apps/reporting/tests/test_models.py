from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.reporting.models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)

from .test_services import M8TestDataMixin


class ReportRunModelTests(M8TestDataMixin, TestCase):
    """
    Tests for the M8 ReportRun model.

    Focus:
        - valid creation
        - lifecycle
        - frozen-state invariants
        - reporting-period protection
        - framework-version protection
        - timestamp behavior
        - metadata behavior
    """

    def test_01_report_run_can_be_created(self):
        run = self.make_report_run()

        self.assertIsNotNone(run.pk)

    def test_02_new_report_run_is_draft(self):
        run = self.make_report_run()

        self.assertEqual(
            run.status,
            ReportRun.Status.DRAFT,
        )

    def test_03_new_report_run_is_not_frozen(self):
        run = self.make_report_run()

        self.assertFalse(run.is_frozen)

    def test_04_new_report_run_has_no_snapshot_timestamp(self):
        run = self.make_report_run()

        self.assertIsNone(run.snapshot_frozen_at)

    def test_05_report_run_has_reporting_period(self):
        run = self.make_report_run()

        self.assertEqual(
            run.reporting_period_id,
            self.period.pk,
        )

    def test_06_report_run_has_framework_version(self):
        run = self.make_report_run()

        self.assertEqual(
            run.framework_version_id,
            self.framework_version.pk,
        )

    def test_07_report_run_has_created_by(self):
        run = self.make_report_run()

        self.assertEqual(
            run.created_by_id,
            self.user.pk,
        )

    def test_08_report_run_metadata_defaults_to_dict(self):
        run = self.make_report_run()

        self.assertIsInstance(
            run.metadata,
            dict,
        )

    def test_09_report_run_metadata_can_store_json(self):
        run = self.make_report_run(
            metadata={
                "purpose": "M8 acceptance test",
                "source": "automated-test",
            }
        )

        self.assertEqual(
            run.metadata["purpose"],
            "M8 acceptance test",
        )

    def test_10_is_frozen_property_false_for_draft(self):
        run = self.make_report_run()

        self.assertFalse(run.is_frozen)

    def test_11_is_frozen_property_true_for_frozen_run(self):
        run = self.make_report_run(
            status=ReportRun.Status.FROZEN,
        )

        self.assertTrue(run.is_frozen)

    def test_12_frozen_run_cannot_change_reporting_period(self):
        run = self.make_report_run(
            status=ReportRun.Status.FROZEN,
        )

        other_period = self.make_reporting_period(
            name="FY 2026-27",
        )

        run.reporting_period = other_period

        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_13_frozen_run_cannot_change_framework_version(self):
        run = self.make_report_run(
            status=ReportRun.Status.FROZEN,
        )

        other_version = self.make_framework_version(
            version_code="GRI-2025",
        )

        run.framework_version = other_version

        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_14_frozen_run_cannot_return_to_draft(self):
        run = self.make_report_run(
            status=ReportRun.Status.FROZEN,
        )

        run.status = ReportRun.Status.DRAFT

        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_15_frozen_run_can_keep_frozen_status(self):
        run = self.make_report_run(
            status=ReportRun.Status.FROZEN,
        )

        run.status = ReportRun.Status.FROZEN

        run.full_clean()

    def test_16_report_run_string_representation(self):
        run = self.make_report_run()

        text = str(run)

        self.assertIn(
            "GRI",
            text,
        )

        self.assertIn(
            "GRI-2021",
            text,
        )

    def test_17_report_run_has_created_timestamp(self):
        run = self.make_report_run()

        self.assertIsNotNone(
            run.created_at,
        )

    def test_18_report_run_has_updated_timestamp(self):
        run = self.make_report_run()

        self.assertIsNotNone(
            run.updated_at,
        )


class FrameworkSnapshotModelTests(M8TestDataMixin, TestCase):

    def test_19_snapshot_can_be_created(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertIsNotNone(
            snapshot.pk,
        )

    def test_20_snapshot_belongs_to_report_run(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertEqual(
            snapshot.report_run_id,
            run.pk,
        )

    def test_21_snapshot_stores_framework_identity(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertEqual(
            snapshot.source_framework_id,
            self.framework.id,
        )

    def test_22_snapshot_stores_framework_version_identity(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertEqual(
            snapshot.source_framework_version_id,
            self.framework_version.id,
        )

    def test_23_snapshot_stores_framework_code(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertEqual(
            snapshot.framework_code,
            "GRI",
        )

    def test_24_snapshot_stores_version_code(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertEqual(
            snapshot.version_code,
            "GRI-2021",
        )

    def test_25_snapshot_can_be_read_after_creation(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertEqual(
            FrameworkSnapshot.objects.get(
                pk=snapshot.pk
            ).pk,
            snapshot.pk,
        )

    def test_26_snapshot_update_is_rejected(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        snapshot.framework_name = "Changed"

        with self.assertRaises(ValidationError):
            snapshot.save()

    def test_27_snapshot_delete_is_rejected(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        with self.assertRaises(ValidationError):
            snapshot.delete()

    def test_28_snapshot_has_frozen_timestamp(self):
        run = self.make_report_run()

        snapshot = self.make_snapshot(run)

        self.assertIsNotNone(
            snapshot.frozen_at,
        )


class SnapshotNodeModelTests(M8TestDataMixin, TestCase):

    def test_29_snapshot_node_can_be_created(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
        )

        self.assertIsNotNone(node.pk)

    def test_30_snapshot_node_belongs_to_snapshot(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
        )

        self.assertEqual(
            node.snapshot_id,
            snapshot.pk,
        )

    def test_31_snapshot_node_stores_source_node_id(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        source_node = self.nodes[0]

        node = self.make_snapshot_node(
            snapshot=snapshot,
            source_node_id=source_node.pk,
        )

        self.assertEqual(
            node.source_node_id,
            source_node.pk,
        )

    def test_32_snapshot_node_stores_code(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
            code="302-1",
        )

        self.assertEqual(
            node.code,
            "302-1",
        )

    def test_33_snapshot_node_stores_title(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
            title="Energy consumption",
        )

        self.assertEqual(
            node.title,
            "Energy consumption",
        )

    def test_34_snapshot_node_parent_can_be_snapshot_node(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        parent = self.make_snapshot_node(
            snapshot=snapshot,
            code="GRI-300",
        )

        child = self.make_snapshot_node(
            snapshot=snapshot,
            code="GRI-302",
            parent=parent,
        )

        self.assertEqual(
            child.parent_id,
            parent.pk,
        )

    def test_35_snapshot_node_update_is_rejected(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
        )

        node.title = "Changed"

        with self.assertRaises(ValidationError):
            node.save()

    def test_36_snapshot_node_delete_is_rejected(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
        )

        with self.assertRaises(ValidationError):
            node.delete()

    def test_37_snapshot_node_metadata_defaults_to_dict(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)

        node = self.make_snapshot_node(
            snapshot=snapshot,
        )

        self.assertIsInstance(
            node.metadata,
            dict,
        )


class SnapshotMappingModelTests(M8TestDataMixin, TestCase):

    def test_38_snapshot_mapping_can_be_created(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
        )

        self.assertIsNotNone(mapping.pk)

    def test_39_snapshot_mapping_belongs_to_snapshot_node(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
        )

        self.assertEqual(
            mapping.snapshot_node_id,
            node.pk,
        )

    def test_40_snapshot_mapping_preserves_canonical_datapoint_code(
        self,
    ):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
            canonical_datapoint_code="ENERGY_TOTAL_CONSUMPTION",
        )

        self.assertEqual(
            mapping.canonical_datapoint_code,
            "ENERGY_TOTAL_CONSUMPTION",
        )

    def test_41_snapshot_mapping_preserves_primary_flag(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
            is_primary=True,
        )

        self.assertTrue(
            mapping.is_primary,
        )

    def test_42_snapshot_mapping_preserves_aggregation(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
            aggregation="SUM",
        )

        self.assertEqual(
            mapping.aggregation,
            "SUM",
        )

    def test_43_snapshot_mapping_update_is_rejected(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
        )

        mapping.canonical_datapoint_code = "CHANGED"

        with self.assertRaises(ValidationError):
            mapping.save()

    def test_44_snapshot_mapping_delete_is_rejected(self):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
        )

        with self.assertRaises(ValidationError):
            mapping.delete()

    def test_45_snapshot_mapping_has_deterministic_display_order(
        self,
    ):
        run = self.make_report_run()
        snapshot = self.make_snapshot(run)
        node = self.make_snapshot_node(snapshot=snapshot)

        mapping = self.make_snapshot_mapping(
            snapshot_node=node,
            display_order=3,
        )

        self.assertEqual(
            mapping.display_order,
            3,
        )