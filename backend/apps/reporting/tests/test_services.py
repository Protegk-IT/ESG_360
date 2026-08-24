from unittest.mock import patch
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.reporting.models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)
from apps.reporting.services import freeze_report_run
from apps.reporting.services import ReportValueResolver

from apps.accounts.models import (
    Permission,
    Role,
    User,
    UserRoleAssignment,
)
from apps.periods.models import ReportingPeriod
from apps.frameworks.models import (
    Framework,
    FrameworkVersion,
    FrameworkNode,
    DatapointMapping,
)
from apps.datapoints.models import (
    DatapointCategory,
    DatapointDataType,
    DatapointOption,
    DatapointTableColumn,
    DatapointTableRow,
)
from apps.modules.models import Module

from apps.datapoints.models import Datapoint

from apps.data_capture.models import SubmissionStatus
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.organizations.models import OrgNode

class M8TestDataMixin:
    """
    Small reusable M8 fixture factory.

    IMPORTANT:
    Adjust only the M3/M7 field names here if your current
    develop branch differs.

    Keep the actual test logic unchanged.
    """

    def setUp(self):
        self.user = self.make_user()

        permission = Permission.objects.create(
            code="report.create_run",
            name="Create report run",
            module_code="report",
            action="CREATE",
        )
        role = Role.objects.create(
            role_code="reporting-test",
            role_name="Reporting Test",
        )
        role.permissions.add(permission)
        UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
        )

        self.period = self.make_reporting_period()

        self.framework = self.make_framework()

        self.module = Module.objects.create(
            code="reporting-test",
            name="Reporting Test",
        )

        self.datapoint_category = DatapointCategory.objects.create(
            code="REPORTING-TEST",
            name="Reporting Test",
            module=self.module,
        )

        self.framework_version = self.make_framework_version(
            framework=self.framework,
        )

        self.nodes = self.make_framework_tree(
            self.framework_version,
        )

    def make_user(self):
        return User.objects.create_user(
            username="m8-test-user",
            email="m8@test.local",
            password="TestPassword123!",
        )

    def make_reporting_period(self, name="FY 2025-26"):
        start_date = "2025-04-01"
        end_date = "2026-03-31"

        if name != "FY 2025-26":
            start_date = "2026-04-01"
            end_date = "2027-03-31"

        return ReportingPeriod.objects.create(
            name=name,
            period_type="ANNUAL",
            start_date=start_date,
            end_date=end_date,
        )

    def make_framework(self, code="GRI"):
        return Framework.objects.create(
            code=code,
            name="Global Reporting Initiative",
            is_enabled=True,
        )

    def make_framework_version(
        self,
        framework=None,
        version_code="GRI-2021",
    ):
        return FrameworkVersion.objects.create(
            framework=framework or self.framework,
            version_code=version_code,
            version_name="GRI 2021",
            is_active=True,
        )

    def make_framework_tree(self, framework_version):
        section = FrameworkNode.objects.create(
            framework_version=framework_version,
            code="TOPIC-STANDARDS",
            title="Topic Standards",
            node_type="SECTION",
            display_order=1,
            depth=0,
            path="/TOPIC-STANDARDS/",
            is_answerable=False,
            is_core=False,
            is_active=True,
        )

        series = FrameworkNode.objects.create(
            framework_version=framework_version,
            parent=section,
            code="GRI-300",
            title="GRI 300 Series",
            node_type="SUBSECTION",
            display_order=1,
            depth=1,
            path="/TOPIC-STANDARDS/GRI-300/",
            is_answerable=False,
            is_core=False,
            is_active=True,
        )

        energy = FrameworkNode.objects.create(
            framework_version=framework_version,
            parent=series,
            code="GRI-302",
            title="Energy",
            node_type="SUBSECTION",
            display_order=1,
            depth=2,
            path="/TOPIC-STANDARDS/GRI-300/GRI-302/",
            is_answerable=False,
            is_core=False,
            is_active=True,
        )

        node_302_1 = FrameworkNode.objects.create(
            framework_version=framework_version,
            parent=energy,
            code="302-1",
            title="Energy consumption",
            node_type="DISCLOSURE",
            display_order=1,
            depth=3,
            path="/TOPIC-STANDARDS/GRI-300/GRI-302/302-1/",
            response_format="NUMERIC",
            is_answerable=True,
            is_core=False,
            is_active=True,
        )

        node_302_2 = FrameworkNode.objects.create(
            framework_version=framework_version,
            parent=energy,
            code="302-2",
            title="Energy consumption outside the organization",
            node_type="DISCLOSURE",
            display_order=2,
            depth=3,
            path="/TOPIC-STANDARDS/GRI-300/GRI-302/302-2/",
            response_format="NUMERIC",
            is_answerable=True,
            is_core=False,
            is_active=True,
        )

        universal = FrameworkNode.objects.create(
            framework_version=framework_version,
            code="UNIVERSAL-STANDARDS",
            title="Universal Standards",
            node_type="SECTION",
            display_order=2,
            depth=0,
            path="/UNIVERSAL-STANDARDS/",
            is_answerable=False,
            is_core=False,
            is_active=True,
        )

        return [
            section,
            series,
            energy,
            node_302_1,
            node_302_2,
            universal,
        ]

    def make_datapoint(
        self,
        code="ENERGY_TOTAL_CONSUMPTION",
    ):
        return Datapoint.objects.create(
            code=code,
            category=self.datapoint_category,
            module=self.module,
            label="Energy total consumption",
            data_type="DECIMAL",
            collection_level="COMPANY",
            frequency="ANNUAL",
            is_active=True,
        )

    def make_mapping(
        self,
        node=None,
        datapoint=None,
        is_primary=True,
    ):
        return DatapointMapping.objects.create(
            framework_node=node or self.nodes[3],
            datapoint=datapoint or self.make_datapoint(),
            mapping_type="DIRECT",
            aggregation="NONE",
            is_primary=is_primary,
            confidence="PROVISIONAL",
            mapping_note="M8 test mapping",
        )

    def make_report_run(self, **kwargs):
        return ReportRun.objects.create(
            reporting_period=kwargs.pop(
                "reporting_period",
                self.period,
            ),
            framework_version=kwargs.pop(
                "framework_version",
                self.framework_version,
            ),
            created_by=kwargs.pop(
                "created_by",
                self.user,
            ),
            **kwargs,
        )

    def make_snapshot(self, run):
        framework = run.framework_version.framework

        return FrameworkSnapshot.objects.create(
            report_run=run,
            source_framework_id=framework.id,
            source_framework_version_id=run.framework_version.id,
            framework_code=framework.code,
            framework_name=framework.name,
            version_code=run.framework_version.version_code,
            version_name=run.framework_version.version_name,
            frozen_at="2026-08-22T10:45:12Z",
        )

    def make_snapshot_node(
        self,
        snapshot,
        parent=None,
        source_node_id=None,
        code="302-1",
        title="Energy consumption",
    ):
        return SnapshotNode.objects.create(
            snapshot=snapshot,
            parent=parent,
            source_node_id=source_node_id,
            code=code,
            title=title,
            node_type="DISCLOSURE",
            display_order=1,
            depth=3,
            path=f"/{code}/",
            response_format="NUMERIC",
            is_answerable=True,
            is_core=False,
            is_active=True,
        )

    def make_snapshot_mapping(
        self,
        snapshot_node,
        canonical_datapoint_code="ENERGY_TOTAL_CONSUMPTION",
        **kwargs,
    ):
        return SnapshotMapping.objects.create(
            snapshot_node=snapshot_node,
            canonical_datapoint_code=canonical_datapoint_code,
            mapping_type=kwargs.pop(
                "mapping_type",
                "DIRECT",
            ),
            aggregation=kwargs.pop(
                "aggregation",
                "NONE",
            ),
            is_primary=kwargs.pop(
                "is_primary",
                True,
            ),
            confidence=kwargs.pop(
                "confidence",
                "PROVISIONAL",
            ),
            mapping_note=kwargs.pop(
                "mapping_note",
                "Test mapping",
            ),
            display_order=kwargs.pop(
                "display_order",
                0,
            ),
            **kwargs,
        )

    def make_capture_company(self):
        from apps.companies.models import Company

        return Company.objects.create(
            company_name="M8 Capture Company",
            company_code="M8CAP",
            contact_person="M8 Owner",
            email="m8capture@example.com",
            mobile_number="1234567890",
        )

    def make_capture_org_node(self, company, code="M8-ROOT"):
        return OrgNode.objects.get(
            company=company,
            node_type="LEGAL_ENTITY",
            parent__isnull=True,
        )

    def make_capture_user(self, username):
        user = User.objects.create_user(
            username=username,
            password="TestPassword123!",
        )

        enter_permission, _ = Permission.objects.get_or_create(
            code="data.enter",
            defaults={
                "name": "Enter data",
                "module_code": "data",
                "action": "EDIT",
            },
        )
        submit_permission, _ = Permission.objects.get_or_create(
            code="data.submit",
            defaults={
                "name": "Submit data",
                "module_code": "data",
                "action": "APPROVE",
            },
        )
        capture_role, _ = Role.objects.get_or_create(
            role_code="reporting-capture",
            defaults={
                "role_name": "Reporting Capture",
            },
        )
        capture_role.permissions.add(
            enter_permission,
            submit_permission,
        )
        UserRoleAssignment.objects.create(
            user=user,
            role=capture_role,
            module_code="data",
        )

        return user

    def make_capture_request(
        self,
        *,
        datapoint,
        org_node,
        reporting_period,
        assignee,
        requester,
    ):
        return DataCaptureLifecycleService.create_request(
            actor=requester,
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=reporting_period,
            assignee=assignee,
        )

    def approve_decimal_submission(
        self,
        *,
        request,
        maker,
        reviewer,
        value,
    ):
        submission = request.submission

        DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=maker,
            decimal_value=value,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=maker,
        )

        DataCaptureLifecycleService.approve(
            submission,
            actor=reviewer,
        )

        submission.refresh_from_db()

        self.assertEqual(
            submission.status,
            SubmissionStatus.APPROVED,
        )

        return submission
class FreezeServiceTests(M8TestDataMixin, TestCase):

    def test_01_freeze_creates_snapshot(self):
        run = self.make_report_run()

        freeze_report_run(run)

        self.assertTrue(
            FrameworkSnapshot.objects.filter(
                report_run=run
            ).exists()
        )

    def test_02_freeze_marks_run_frozen(self):
        run = self.make_report_run()

        result = freeze_report_run(run)

        self.assertEqual(
            result.status,
            ReportRun.Status.FROZEN,
        )

    def test_03_freeze_sets_snapshot_frozen_at(self):
        run = self.make_report_run()

        freeze_report_run(run)

        run.refresh_from_db()

        self.assertIsNotNone(
            run.snapshot_frozen_at
        )

    def test_04_freeze_sets_snapshot_frozen_timestamp(self):
        run = self.make_report_run()

        freeze_report_run(run)
        run.refresh_from_db()

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertIsNotNone(
            snapshot.frozen_at
        )

    def test_05_snapshot_copies_framework_code(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            snapshot.framework_code,
            self.framework.code,
        )

    def test_06_snapshot_copies_framework_name(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            snapshot.framework_name,
            self.framework.name,
        )

    def test_07_snapshot_copies_version_code(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            snapshot.version_code,
            self.framework_version.version_code,
        )

    def test_08_all_m7_nodes_are_copied(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            snapshot.nodes.count(),
            len(self.nodes),
        )

    def test_09_source_node_ids_are_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        source_ids = set(
            snapshot.nodes.values_list(
                "source_node_id",
                flat=True,
            )
        )

        expected_ids = {
            node.pk
            for node in self.nodes
        }

        self.assertEqual(
            source_ids,
            expected_ids,
        )

    def test_10_node_codes_are_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        actual = set(
            snapshot.nodes.values_list(
                "code",
                flat=True,
            )
        )

        expected = {
            node.code
            for node in self.nodes
        }

        self.assertEqual(
            actual,
            expected,
        )

    def test_11_node_titles_are_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        original = {
            node.code: node.title
            for node in self.nodes
        }

        actual = {
            node.code: node.title
            for node in snapshot.nodes.all()
        }

        self.assertEqual(
            actual,
            original,
        )

    def test_12_parent_relationships_are_recreated(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        snapshot_by_source = {
            node.source_node_id: node
            for node in snapshot.nodes.all()
        }

        for source_node in self.nodes:
            snapshot_node = snapshot_by_source[
                source_node.pk
            ]

            if source_node.parent_id is None:
                self.assertIsNone(
                    snapshot_node.parent_id
                )
            else:
                self.assertEqual(
                    snapshot_node.parent.source_node_id,
                    source_node.parent_id,
                )

    def test_13_root_nodes_have_no_snapshot_parent(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        roots = snapshot.nodes.filter(
            parent__isnull=True
        )

        expected_root_count = sum(
            1
            for node in self.nodes
            if node.parent_id is None
        )

        self.assertEqual(
            roots.count(),
            expected_root_count,
        )

    def test_14_depth_is_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        original = {
            node.code: node.depth
            for node in self.nodes
        }

        actual = {
            node.code: node.depth
            for node in snapshot.nodes.all()
        }

        self.assertEqual(
            actual,
            original,
        )

    def test_15_path_is_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        original = {
            node.code: node.path
            for node in self.nodes
        }

        actual = {
            node.code: node.path
            for node in snapshot.nodes.all()
        }

        self.assertEqual(
            actual,
            original,
        )

    def test_16_answerability_is_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        original = {
            node.code: node.is_answerable
            for node in self.nodes
        }

        actual = {
            node.code: node.is_answerable
            for node in snapshot.nodes.all()
        }

        self.assertEqual(
            actual,
            original,
        )

    def test_17_core_flag_is_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        original = {
            node.code: node.is_core
            for node in self.nodes
        }

        actual = {
            node.code: node.is_core
            for node in snapshot.nodes.all()
        }

        self.assertEqual(
            actual,
            original,
        )

    def test_18_response_format_is_preserved(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        original = {
            node.code: node.response_format
            for node in self.nodes
        }

        actual = {
            node.code: node.response_format
            for node in snapshot.nodes.all()
        }

        self.assertEqual(
            actual,
            original,
        )

    def test_19_mapping_is_copied(self):
        datapoint = self.make_datapoint()

        self.make_mapping(
            node=self.nodes[3],
            datapoint=datapoint,
        )

        run = self.make_report_run()

        freeze_report_run(run)

        self.assertEqual(
            SnapshotMapping.objects.count(),
            1,
        )

    def test_20_canonical_datapoint_code_is_copied(self):
        datapoint = self.make_datapoint(
            code="ENERGY_TOTAL_CONSUMPTION",
        )

        self.make_mapping(
            node=self.nodes[3],
            datapoint=datapoint,
        )

        run = self.make_report_run()

        freeze_report_run(run)

        mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            mapping.canonical_datapoint_code,
            "ENERGY_TOTAL_CONSUMPTION",
        )

    def test_21_source_mapping_id_is_copied(self):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.source_mapping_id,
            mapping.pk,
        )

    def test_22_source_datapoint_id_is_copied(self):
        datapoint = self.make_datapoint()

        mapping = self.make_mapping(
            datapoint=datapoint,
        )

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.source_datapoint_id,
            datapoint.pk,
        )

    def test_23_mapping_type_is_copied(self):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.mapping_type,
            mapping.mapping_type,
        )

    def test_24_aggregation_is_copied(self):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.aggregation,
            mapping.aggregation,
        )

    def test_25_primary_flag_is_copied(self):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.is_primary,
            mapping.is_primary,
        )

    def test_26_confidence_is_copied(self):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.confidence,
            mapping.confidence,
        )

    def test_27_mapping_note_is_copied(self):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get()

        self.assertEqual(
            snapshot_mapping.mapping_note,
            mapping.mapping_note,
        )

    def test_28_mapping_order_is_deterministic(self):
        datapoint_a = self.make_datapoint(
            code="ENERGY_A",
        )

        datapoint_b = self.make_datapoint(
            code="ENERGY_B",
        )

        self.make_mapping(
            node=self.nodes[3],
            datapoint=datapoint_b,
            is_primary=False,
        )

        self.make_mapping(
            node=self.nodes[3],
            datapoint=datapoint_a,
        )

        run = self.make_report_run()

        freeze_report_run(run)

        mappings = list(
            SnapshotMapping.objects
            .filter(
                snapshot_node__code="302-1"
            )
            .order_by("display_order")
        )

        self.assertEqual(
            mappings[0].canonical_datapoint_code,
            "ENERGY_A",
        )

        self.assertEqual(
            mappings[1].canonical_datapoint_code,
            "ENERGY_B",
        )

    def test_29_re_freeze_is_rejected(self):
        run = self.make_report_run()

        freeze_report_run(run)

        with self.assertRaises(ValidationError):
            freeze_report_run(run)

    def test_30_re_freeze_does_not_create_second_snapshot(
        self,
    ):
        run = self.make_report_run()

        freeze_report_run(run)

        with self.assertRaises(ValidationError):
            freeze_report_run(run)

        self.assertEqual(
            FrameworkSnapshot.objects.filter(
                report_run=run
            ).count(),
            1,
        )

    def test_31_frozen_report_run_context_is_locked(self):
        run = self.make_report_run()

        freeze_report_run(run)

        run.refresh_from_db()

        self.assertEqual(
            run.framework_version_id,
            self.framework_version.pk,
        )

        self.assertEqual(
            run.reporting_period_id,
            self.period.pk,
        )

    def test_32_live_node_edit_does_not_change_snapshot(self):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_node = SnapshotNode.objects.get(
            source_node_id=self.nodes[3].pk
        )

        original_title = snapshot_node.title

        self.nodes[3].title = "LIVE M7 CHANGED TITLE"
        self.nodes[3].save()

        snapshot_node.refresh_from_db()

        self.assertEqual(
            snapshot_node.title,
            original_title,
        )

    def test_33_live_node_order_edit_does_not_change_snapshot(
        self,
    ):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_node = SnapshotNode.objects.get(
            source_node_id=self.nodes[3].pk
        )

        original_order = snapshot_node.display_order

        self.nodes[3].display_order = 999
        self.nodes[3].save()

        snapshot_node.refresh_from_db()

        self.assertEqual(
            snapshot_node.display_order,
            original_order,
        )

    def test_34_live_node_path_edit_does_not_change_snapshot(
        self,
    ):
        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_node = SnapshotNode.objects.get(
            source_node_id=self.nodes[3].pk
        )

        original_path = snapshot_node.path

        self.nodes[3].path = "/CHANGED/PATH/"
        self.nodes[3].save()

        snapshot_node.refresh_from_db()

        self.assertEqual(
            snapshot_node.path,
            original_path,
        )

    def test_35_live_mapping_edit_does_not_change_snapshot(
        self,
    ):
        datapoint = self.make_datapoint()

        mapping = self.make_mapping(
            datapoint=datapoint,
        )

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get(
            source_mapping_id=mapping.pk
        )

        original_code = (
            snapshot_mapping.canonical_datapoint_code
        )

        datapoint.code = "CHANGED_DATAPOINT_CODE"
        datapoint.save()

        snapshot_mapping.refresh_from_db()

        self.assertEqual(
            snapshot_mapping.canonical_datapoint_code,
            original_code,
        )

    def test_36_live_mapping_metadata_edit_does_not_change_snapshot(
        self,
    ):
        mapping = self.make_mapping()

        run = self.make_report_run()

        freeze_report_run(run)

        snapshot_mapping = SnapshotMapping.objects.get(
            source_mapping_id=mapping.pk
        )

        original_note = snapshot_mapping.mapping_note

        mapping.mapping_note = "CHANGED LIVE M7 NOTE"
        mapping.save()

        snapshot_mapping.refresh_from_db()

        self.assertEqual(
            snapshot_mapping.mapping_note,
            original_note,
        )

    def test_37_freeze_is_transactional_on_failure(self):
        run = self.make_report_run()
        self.make_mapping()

        with patch(
            "apps.reporting.services.SnapshotMapping.objects.create",
            side_effect=RuntimeError(
                "Forced freeze failure"
            ),
        ):
            with self.assertRaises(RuntimeError):
                freeze_report_run(run)

        run.refresh_from_db()

        self.assertEqual(
            run.status,
            ReportRun.Status.DRAFT,
        )

        self.assertIsNone(
            run.snapshot_frozen_at,
        )

        self.assertEqual(
            FrameworkSnapshot.objects.filter(
                report_run=run
            ).count(),
            0,
        )

        self.assertEqual(
            SnapshotNode.objects.count(),
            0,
        )

        self.assertEqual(
            SnapshotMapping.objects.count(),
            0,
        )

    def test_38_failed_freeze_does_not_leave_partial_snapshot(
        self,
    ):
        run = self.make_report_run()

        with patch(
            "apps.reporting.services.SnapshotNode.objects.create",
            side_effect=RuntimeError(
                "Forced node failure"
            ),
        ):
            with self.assertRaises(RuntimeError):
                freeze_report_run(run)

        self.assertFalse(
            FrameworkSnapshot.objects.filter(
                report_run=run
            ).exists()
        )

    def test_39_freeze_returns_report_run(self):
        run = self.make_report_run()

        result = freeze_report_run(run)

        self.assertIsInstance(
            result,
            ReportRun,
        )

    def test_40_freeze_result_is_frozen(self):
        run = self.make_report_run()

        result = freeze_report_run(run)

        self.assertTrue(
            result.is_frozen,
        )


class ReportValueResolverTests(M8TestDataMixin, TestCase):

    def _prepare_frozen_mapping(self):
        datapoint = self.make_datapoint(
            code="ENERGY-TOTAL",
        )

        self.make_mapping(
            node=self.nodes[3],
            datapoint=datapoint,
        )

        run = self.make_report_run()

        freeze_report_run(run)
        run.refresh_from_db()

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run,
        )

        snapshot_node = snapshot.nodes.get(
            code="302-1",
        )

        mapping = snapshot_node.mappings.get()

        return run, datapoint, mapping

    def _make_capture_context(self):
        company = self.make_capture_company()

        org_node = self.make_capture_org_node(
            company,
        )

        requester = self.make_capture_user(
            "capture-requester",
        )

        maker = self.make_capture_user(
            "capture-maker",
        )

        reviewer = self.make_capture_user(
            "capture-reviewer",
        )

        return (
            org_node,
            requester,
            maker,
            reviewer,
        )

    def test_41_approved_value_is_resolved(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        (
            org_node,
            requester,
            maker,
            reviewer,
        ) = self._make_capture_context()

        request = self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        )

        self.approve_decimal_submission(
            request=request,
            maker=maker,
            reviewer=reviewer,
            value="125.50",
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            len(resolved),
            1,
        )

        self.assertEqual(
            resolved[0]["status"],
            "RESOLVED",
        )

        self.assertEqual(
            resolved[0]["value"],
            125.50,
        )

        self.assertEqual(
            resolved[0]["canonical_datapoint_code"],
            "ENERGY-TOTAL",
        )

    def test_42_draft_submission_is_not_resolved(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        (
            org_node,
            requester,
            maker,
            reviewer,
        ) = self._make_capture_context()

        request = self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        )

        DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=maker,
            decimal_value="100.00",
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            len(resolved),
            1,
        )

        self.assertEqual(
            resolved[0]["status"],
            "UNRESOLVED",
        )

        self.assertIsNone(
            resolved[0]["value"],
        )

    def test_43_submitted_submission_is_not_resolved(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        (
            org_node,
            requester,
            maker,
            reviewer,
        ) = self._make_capture_context()

        request = self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        )

        DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=maker,
            decimal_value="200.00",
        )

        DataCaptureLifecycleService.submit(
            request.submission,
            actor=maker,
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            resolved[0]["status"],
            "UNRESOLVED",
        )

    def test_44_rejected_submission_is_not_resolved(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        (
            org_node,
            requester,
            maker,
            reviewer,
        ) = self._make_capture_context()

        request = self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        )

        DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=maker,
            decimal_value="300.00",
        )

        DataCaptureLifecycleService.submit(
            request.submission,
            actor=maker,
        )

        DataCaptureLifecycleService.reject(
            request.submission,
            actor=reviewer,
            reason="Needs correction.",
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            resolved[0]["status"],
            "UNRESOLVED",
        )

    def test_45_wrong_reporting_period_is_not_resolved(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        (
            org_node,
            requester,
            maker,
            reviewer,
        ) = self._make_capture_context()

        wrong_period = ReportingPeriod.objects.create(
            name="Wrong Period",
            period_type="ANNUAL",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        )

        request = self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=wrong_period,
            assignee=maker,
            requester=requester,
        )

        self.approve_decimal_submission(
            request=request,
            maker=maker,
            reviewer=reviewer,
            value="500.00",
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            resolved[0]["status"],
            "UNRESOLVED",
        )

        self.assertIsNone(
            resolved[0]["value"],
        )

    def test_46_no_approved_value_returns_unresolved(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            len(resolved),
            1,
        )

        self.assertEqual(
            resolved[0]["status"],
            "UNRESOLVED",
        )

        self.assertIsNone(
            resolved[0]["value"],
        )

    def test_47_unfrozen_report_run_cannot_be_resolved(self):
        run = self.make_report_run()

        with self.assertRaises(ValidationError):
            ReportValueResolver.build_dataset(
                run,
            )

    def test_48_m5_data_is_not_mutated(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        (
            org_node,
            requester,
            maker,
            reviewer,
        ) = self._make_capture_context()

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
            value="750.00",
        )

        answer = submission.answer

        original_value = answer.decimal_value
        original_status = submission.status

        ReportValueResolver.build_dataset(
            run,
        )

        answer.refresh_from_db()
        submission.refresh_from_db()

        self.assertEqual(
            answer.decimal_value,
            original_value,
        )

        self.assertEqual(
            submission.status,
            original_status,
        )

    def test_49_multiple_approved_values_are_deterministic(self):
        run, datapoint, mapping = (
            self._prepare_frozen_mapping()
        )

        company = self.make_capture_company()

        root = self.make_capture_org_node(
            company,
            code="M8-ROOT",
        )

        requester = self.make_capture_user(
            "multi-requester",
        )

        maker_one = self.make_capture_user(
            "maker-one",
        )

        maker_two = self.make_capture_user(
            "maker-two",
        )

        reviewer = self.make_capture_user(
            "multi-reviewer",
        )

        child_one = OrgNode.objects.create(
            company=company,
            parent=root,
            node_type="BUSINESS_UNIT",
            code="BU-01",
            name="Business Unit 01",
        )

        child_two = OrgNode.objects.create(
            company=company,
            parent=root,
            node_type="BUSINESS_UNIT",
            code="BU-02",
            name="Business Unit 02",
        )

        request_one = self.make_capture_request(
            datapoint=datapoint,
            org_node=child_one,
            reporting_period=self.period,
            assignee=maker_one,
            requester=requester,
        )

        request_two = self.make_capture_request(
            datapoint=datapoint,
            org_node=child_two,
            reporting_period=self.period,
            assignee=maker_two,
            requester=requester,
        )

        self.approve_decimal_submission(
            request=request_one,
            maker=maker_one,
            reviewer=reviewer,
            value="100.00",
        )

        self.approve_decimal_submission(
            request=request_two,
            maker=maker_two,
            reviewer=reviewer,
            value="200.00",
        )

        dataset = ReportValueResolver.build_dataset(
            run,
        )

        resolved = [
            item
            for item in dataset
            if item["snapshot_mapping_id"] == mapping.id
        ]

        self.assertEqual(
            len(resolved),
            2,
        )

        self.assertEqual(
            [item["value"] for item in resolved],
            [100.00, 200.00],
        )


class ReportValueResolverContractTests(M8TestDataMixin, TestCase):

    def make_capture_context(self):
        company = self.make_capture_company()
        org_node = self.make_capture_org_node(company)
        return (
            org_node,
            self.make_capture_user("contract-requester"),
            self.make_capture_user("contract-maker"),
            self.make_capture_user("contract-reviewer"),
        )

    def make_contract_datapoint(self, code, data_type, **kwargs):
        return Datapoint.objects.create(
            code=code,
            category=self.datapoint_category,
            module=self.module,
            label=code,
            data_type=data_type,
            collection_level="ORG_NODE",
            frequency="ANNUAL",
            is_active=True,
            **kwargs,
        )

    def make_capture_request_for(self, datapoint, context):
        org_node, requester, maker, reviewer = context
        return self.make_capture_request(
            datapoint=datapoint,
            org_node=org_node,
            reporting_period=self.period,
            assignee=maker,
            requester=requester,
        ), maker, reviewer

    def approve_scalar(self, request, maker, reviewer, field_name, value):
        DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=maker,
            **{field_name: value},
        )
        DataCaptureLifecycleService.submit(
            request.submission,
            actor=maker,
        )
        DataCaptureLifecycleService.approve(
            request.submission,
            actor=reviewer,
        )

    def test_primitive_types_and_provenance_are_preserved(self):
        context = self.make_capture_context()
        primitive_cases = [
            (DatapointDataType.DECIMAL, "decimal_value", Decimal("12.50")),
            (DatapointDataType.INTEGER, "integer_value", 12),
            (DatapointDataType.TEXT, "text_value", "short text"),
            (DatapointDataType.LONG_TEXT, "text_value", "long text"),
            (DatapointDataType.BOOLEAN, "boolean_value", False),
            (DatapointDataType.DATE, "date_value", date(2026, 8, 24)),
        ]
        datapoints = []
        requests = []
        for index, (data_type, field_name, value) in enumerate(primitive_cases):
            datapoint = self.make_contract_datapoint(
                f"CONTRACT-{index}",
                data_type,
            )
            self.make_mapping(
                node=self.nodes[3],
                datapoint=datapoint,
                is_primary=index == 0,
            )
            datapoints.append(datapoint)

        select_datapoint = self.make_contract_datapoint(
            "CONTRACT-SELECT",
            DatapointDataType.SELECT,
        )
        select_option = DatapointOption.objects.create(
            datapoint=select_datapoint,
            code="YES",
            label="Yes",
        )
        self.make_mapping(
            node=self.nodes[3],
            datapoint=select_datapoint,
            is_primary=False,
        )
        datapoints.append(select_datapoint)

        run = self.make_report_run()
        freeze_report_run(run)
        run.refresh_from_db()

        for datapoint, case in zip(datapoints[:-1], primitive_cases):
            request, maker, reviewer = self.make_capture_request_for(
                datapoint,
                context,
            )
            self.approve_scalar(
                request,
                maker,
                reviewer,
                case[1],
                case[2],
            )
            requests.append(request)

        request, maker, reviewer = self.make_capture_request_for(
            select_datapoint,
            context,
        )
        self.approve_scalar(
            request,
            maker,
            reviewer,
            "selected_option",
            select_option,
        )
        requests.append(request)

        dataset = ReportValueResolver.build_dataset(run)
        resolved = {
            item["canonical_datapoint_code"]: item
            for item in dataset
            if item["status"] == "RESOLVED"
        }

        for datapoint, case in zip(datapoints[:-1], primitive_cases):
            item = resolved[datapoint.code]
            self.assertEqual(item["data_type"], case[0])
            self.assertEqual(item["value"], case[2])
            self.assertEqual(item["data_request_id"], requests[datapoints.index(datapoint)].id)
            self.assertEqual(item["provenance"]["source_type"], "CAPTURED")
            self.assertIsNotNone(item["provenance"]["approved_by"])
            self.assertIsNotNone(item["provenance"]["approved_at"])
            self.assertIsNotNone(item["provenance"]["entered_by"])

        self.assertEqual(
            resolved[select_datapoint.code]["value"]["code"],
            "YES",
        )

    def test_table_preserves_fixed_and_dynamic_rows(self):
        context = self.make_capture_context()
        datapoint = self.make_contract_datapoint(
            "CONTRACT-TABLE",
            DatapointDataType.TABLE,
            allow_dynamic_rows=True,
        )
        quantity = DatapointTableColumn.objects.create(
            datapoint=datapoint,
            code="quantity",
            label="Quantity",
            data_type=DatapointDataType.INTEGER,
            display_order=1,
        )
        note = DatapointTableColumn.objects.create(
            datapoint=datapoint,
            code="note",
            label="Note",
            data_type=DatapointDataType.TEXT,
            display_order=2,
        )
        fixed_row = DatapointTableRow.objects.create(
            datapoint=datapoint,
            code="fixed-1",
            label="Fixed row",
            display_order=1,
        )
        self.make_mapping(node=self.nodes[3], datapoint=datapoint)
        run = self.make_report_run()
        freeze_report_run(run)
        run.refresh_from_db()

        request, maker, reviewer = self.make_capture_request_for(
            datapoint,
            context,
        )
        DataCaptureLifecycleService.save_table_row(
            request.submission,
            actor=maker,
            definition_row=fixed_row,
            cells=[
                {"column": quantity, "integer_value": 4},
                {"column": note, "text_value": "fixed value"},
            ],
        )
        DataCaptureLifecycleService.save_table_row(
            request.submission,
            actor=maker,
            label="Dynamic row",
            display_order=2,
            cells=[{"column": quantity, "integer_value": 8}],
        )
        DataCaptureLifecycleService.submit(request.submission, actor=maker)
        DataCaptureLifecycleService.approve(request.submission, actor=reviewer)

        item = ReportValueResolver.build_dataset(run)[0]
        self.assertEqual(item["data_type"], DatapointDataType.TABLE)
        self.assertEqual(len(item["value"]), 2)
        self.assertEqual(item["value"][0]["definition_row"]["code"], "fixed-1")
        self.assertEqual(item["value"][0]["cells"][0]["value"], 4)
        self.assertEqual(item["value"][1]["label"], "Dynamic row")
        self.assertEqual(item["value"][1]["cells"][0]["value"], 8)

    def test_resolution_uses_bounded_query_count_for_many_mappings(self):
        for index in range(3):
            datapoint = self.make_contract_datapoint(
                f"QUERY-{index}",
                DatapointDataType.INTEGER,
            )
            self.make_mapping(
                node=self.nodes[3],
                datapoint=datapoint,
                is_primary=index == 0,
            )

        run = self.make_report_run()
        freeze_report_run(run)
        run.refresh_from_db()

        with CaptureQueriesContext(connection) as queries:
            ReportValueResolver.build_dataset(run)

        self.assertLessEqual(len(queries), 8)

    def test_approved_value_for_wrong_datapoint_is_excluded(self):
        context = self.make_capture_context()
        mapped_datapoint = self.make_contract_datapoint(
            "MAPPED-DATAPOINT",
            DatapointDataType.INTEGER,
        )
        wrong_datapoint = self.make_contract_datapoint(
            "WRONG-DATAPOINT",
            DatapointDataType.INTEGER,
        )
        mapping = self.make_mapping(
            node=self.nodes[3],
            datapoint=mapped_datapoint,
        )
        run = self.make_report_run()
        freeze_report_run(run)
        run.refresh_from_db()

        request, maker, reviewer = self.make_capture_request_for(
            wrong_datapoint,
            context,
        )
        self.approve_scalar(
            request,
            maker,
            reviewer,
            "integer_value",
            99,
        )

        dataset = ReportValueResolver.build_dataset(run)
        self.assertEqual(len(dataset), 1)
        item = dataset[0]
        self.assertEqual(item["canonical_datapoint_code"], mapped_datapoint.code)
        self.assertNotEqual(item["canonical_datapoint_code"], wrong_datapoint.code)
        self.assertEqual(item["status"], "UNRESOLVED")
        self.assertIsNone(item["value"])

    def test_query_count_is_bounded_with_approved_values(self):
        datapoints = []
        for index in range(3):
            datapoint = self.make_contract_datapoint(
                f"APPROVED-QUERY-{index}",
                DatapointDataType.INTEGER,
            )
            self.make_mapping(
                node=self.nodes[3],
                datapoint=datapoint,
                is_primary=index == 0,
            )
            datapoints.append(datapoint)

        run = self.make_report_run()
        freeze_report_run(run)
        run.refresh_from_db()

        request, maker, reviewer = self.make_capture_request_for(
            datapoints[0],
            self.make_capture_context(),
        )
        self.approve_scalar(
            request,
            maker,
            reviewer,
            "integer_value",
            10,
        )

        with CaptureQueriesContext(connection) as queries:
            ReportValueResolver.build_dataset(run)

        self.assertLessEqual(len(queries), 8)

    def test_live_mapping_edit_after_freeze_does_not_change_resolution(self):
        context = self.make_capture_context()
        original_datapoint = self.make_contract_datapoint(
            "FROZEN-DATAPOINT",
            DatapointDataType.INTEGER,
        )
        replacement_datapoint = self.make_contract_datapoint(
            "REPLACEMENT-DATAPOINT",
            DatapointDataType.INTEGER,
        )
        live_mapping = self.make_mapping(
            node=self.nodes[3],
            datapoint=original_datapoint,
        )
        run = self.make_report_run()
        freeze_report_run(run)
        run.refresh_from_db()

        live_mapping.datapoint = replacement_datapoint
        live_mapping.save()

        request, maker, reviewer = self.make_capture_request_for(
            original_datapoint,
            context,
        )
        self.approve_scalar(
            request,
            maker,
            reviewer,
            "integer_value",
            42,
        )

        item = ReportValueResolver.build_dataset(run)[0]
        self.assertEqual(item["canonical_datapoint_code"], "FROZEN-DATAPOINT")
        self.assertEqual(item["source_datapoint_id"], original_datapoint.id)
        self.assertNotEqual(item["snapshot_mapping_id"], live_mapping.id)
        self.assertEqual(item["value"], 42)