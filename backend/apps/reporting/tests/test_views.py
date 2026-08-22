import uuid
from unittest.mock import patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
)
from apps.frameworks.models import (
    DatapointMapping,
    Framework,
    FrameworkNode,
    FrameworkVersion,
)
from apps.modules.models import Module
from apps.periods.models import (
    PeriodType,
    ReportingPeriod,
)

from apps.reporting.models import (
    FrameworkSnapshot,
    ReportRun,
    SnapshotMapping,
    SnapshotNode,
)


# ============================================================
# TEST HELPERS
# ============================================================


class ReportingViewTestMixin:
    """
    Shared fixtures and helpers for M8 reporting API tests.
    """

    permission_patch = (
        "apps.accounts.permissions."
        "HasRolePermission.has_permission"
    )

    def create_user(
        self,
        username="m8_test_user",
        is_superuser=False,
    ):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword",
            full_name="M8 Test User",
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )

    def create_module(self):
        """
        M4 Datapoint requires a valid Module.

        The repository's existing framework tests use:
            esg_pillar="E"
        """
        module, _ = Module.objects.get_or_create(
            code="energy",
            defaults={
                "name": "Energy",
                "description": "Energy module for M8 tests",
                "esg_pillar": "E",
                "icon": "zap",
                "is_core": False,
                "is_enabled": True,
                "display_order": 1,
            },
        )
        return module

    def create_datapoint(
        self,
        code=None,
        label=None,
        is_active=True,
    ):
        """
        Create a valid M4 Datapoint using the actual M4 model contract.
        """
        code = code or f"DP_{uuid.uuid4().hex[:10].upper()}"
        label = label or f"Datapoint {code}"

        module = self.create_module(self)

        category = DatapointCategory.objects.create(
            code=f"CAT_{uuid.uuid4().hex[:10].upper()}",
            name=f"Category {code}",
            description="M8 test category",
            module=module,
            esg_pillar="E",
            display_order=1,
            is_active=True,
        )

        return Datapoint.objects.create(
            code=code,
            category=category,
            module=module,
            label=label,
            description="M8 test datapoint",
            data_type=DatapointDataType.DECIMAL,
            collection_level=CollectionLevel.COMPANY,
            frequency=CollectionFrequency.ANNUAL,
            is_required=False,
            allow_dynamic_rows=False,
            validation_metadata={},
            display_order=1,
            is_active=is_active,
        )

    def create_reporting_period(
        self,
        name=None,
        period_type=PeriodType.ANNUAL,
        start_date=None,
        end_date=None,
    ):
        """
        Create a valid M3 ReportingPeriod.

        Annual periods cannot overlap, therefore alternate periods
        in tests can use different years or a non-annual period type.
        """
        from datetime import date

        if name is None:
            name = f"Period {uuid.uuid4().hex[:8]}"

        if start_date is None:
            start_date = date(2025, 4, 1)

        if end_date is None:
            end_date = date(2026, 3, 31)

        return ReportingPeriod.objects.create(
            name=name,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            status="OPEN",
            is_baseline_year=False,
            is_active=True,
        )

    def create_framework(self):
        return Framework.objects.create(
            code=f"GRI_{uuid.uuid4().hex[:6].upper()}",
            name="Global Reporting Initiative",
            description="M8 test framework",
            is_enabled=True,
        )

    def create_framework_version(
        self,
        framework,
        version_code=None,
        version_name=None,
    ):
        version_code = (
            version_code
            or f"GRI-{uuid.uuid4().hex[:6].upper()}"
        )

        version_name = (
            version_name
            or f"GRI Test Version {version_code}"
        )

        return FrameworkVersion.objects.create(
            framework=framework,
            version_code=version_code,
            version_name=version_name,
            effective_from=None,
            effective_to=None,
            published_at=None,
            is_active=True,
            is_default=False,
        )

    def create_node(
        self,
        framework_version,
        code,
        title,
        node_type=FrameworkNode.NodeType.SECTION,
        parent=None,
        display_order=0,
        is_answerable=False,
        is_core=False,
        is_active=True,
    ):
        return FrameworkNode.objects.create(
            framework_version=framework_version,
            parent=parent,
            code=code,
            title=title,
            description=f"Description for {code}",
            instructions=f"Instructions for {code}",
            node_type=node_type,
            display_order=display_order,
            response_format="TEXT",
            is_answerable=is_answerable,
            is_core=is_core,
            is_active=is_active,
        )

    def create_mapping(
        self,
        node,
        datapoint,
        is_primary=False,
    ):
        return DatapointMapping.objects.create(
            framework_node=node,
            datapoint=datapoint,
            mapping_type=DatapointMapping.MappingType.DIRECT,
            aggregation=DatapointMapping.Aggregation.NONE,
            transform_expression="",
            is_primary=is_primary,
            confidence=DatapointMapping.Confidence.CONFIRMED,
            mapping_note="M8 API test mapping",
            reviewed_at=None,
        )

    def create_report_run(
        self,
        reporting_period=None,
        framework_version=None,
        created_by=None,
        metadata=None,
    ):
        return ReportRun.objects.create(
            reporting_period=(
                reporting_period or self.reporting_period
            ),
            framework_version=(
                framework_version or self.framework_version
            ),
            created_by=(
                created_by or self.user
            ),
            metadata=metadata or {},
        )

    def freeze_run(self, report_run):
        from apps.reporting.services import freeze_report_run

        return freeze_report_run(report_run)

    def report_run_url(self, run_id):
        return (
            f"/api/reporting/report-runs/{run_id}/"
        )

    def freeze_url(self, run_id):
        return (
            f"/api/reporting/report-runs/"
            f"{run_id}/freeze/"
        )

    def snapshot_url(self, run_id):
        return (
            f"/api/reporting/report-runs/"
            f"{run_id}/snapshot/"
        )


# ============================================================
# BASE TEST SETUP
# ============================================================


class BaseReportingViewTests(
    ReportingViewTestMixin,
    APITestCase,
):

    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_user(
            cls,
            username="m8_admin",
            is_superuser=True,
        )

        cls.normal_user = cls.create_user(
            cls,
            username="m8_normal_user",
            is_superuser=False,
        )

        cls.reporting_period = cls.create_reporting_period(
            cls,
            name="FY 2025-26",
            start_date=__import__("datetime").date(
                2025,
                4,
                1,
            ),
            end_date=__import__("datetime").date(
                2026,
                3,
                31,
            ),
        )

        cls.second_period = cls.create_reporting_period(
            cls,
            name="May 2026",
            period_type=PeriodType.MONTHLY,
            start_date=__import__("datetime").date(
                2026,
                5,
                1,
            ),
            end_date=__import__("datetime").date(
                2026,
                5,
                31,
            ),
        )

        cls.framework = cls.create_framework(cls)

        cls.framework_version = cls.create_framework_version(
            cls,
            framework=cls.framework,
            version_code="GRI-2021",
            version_name="GRI 2021",
        )

        cls.second_framework_version = (
            cls.create_framework_version(
                cls,
                framework=cls.framework,
                version_code="GRI-2022",
                version_name="GRI 2022",
            )
        )

        # ----------------------------------------------------
        # Representative multi-level M7 tree
        # ----------------------------------------------------

        cls.root_node = cls.create_node(
            cls,
            framework_version=cls.framework_version,
            code="UNIVERSAL",
            title="Universal Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=1,
        )

        cls.energy_section = cls.create_node(
            cls,
            framework_version=cls.framework_version,
            code="GRI-300",
            title="Topic Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            parent=cls.root_node,
            display_order=1,
        )

        cls.energy_subsection = cls.create_node(
            cls,
            framework_version=cls.framework_version,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            parent=cls.energy_section,
            display_order=1,
        )

        cls.node_302_1 = cls.create_node(
            cls,
            framework_version=cls.framework_version,
            code="302-1",
            title="Energy consumption within the organization",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            parent=cls.energy_subsection,
            display_order=1,
            is_answerable=True,
            is_core=True,
        )

        cls.node_302_2 = cls.create_node(
            cls,
            framework_version=cls.framework_version,
            code="302-2",
            title="Energy consumption outside of the organization",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            parent=cls.energy_subsection,
            display_order=2,
            is_answerable=True,
            is_core=False,
        )

        cls.datapoint_1 = cls.create_datapoint(
            cls,
            code="ENERGY_TOTAL_CONSUMPTION",
            label="Energy Total Consumption",
        )

        cls.datapoint_2 = cls.create_datapoint(
            cls,
            code="ENERGY_DESCRIPTION",
            label="Energy Description",
        )

        cls.mapping_1 = cls.create_mapping(
            cls,
            node=cls.node_302_1,
            datapoint=cls.datapoint_1,
            is_primary=True,
        )

        cls.mapping_2 = cls.create_mapping(
            cls,
            node=cls.node_302_2,
            datapoint=cls.datapoint_2,
            is_primary=True,
        )

    def setUp(self):
        self.client.force_authenticate(
            user=self.user,
        )


# ============================================================
# 1-10: AUTHENTICATION / BASIC LIST TESTS
# ============================================================


class ReportRunAuthenticationTests(
    BaseReportingViewTests,
):

    def test_01_authenticated_list_allowed(self):
        response = self.client.get(
            "/api/reporting/report-runs/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_02_authenticated_create_allowed_for_superuser(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
                "metadata": {},
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_03_unauthenticated_list_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            "/api/reporting/report-runs/"
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_04_unauthenticated_create_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_05_unauthenticated_detail_rejected(self):
        run = self.create_report_run()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.report_run_url(run.id)
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_06_unauthenticated_freeze_rejected(self):
        run = self.create_report_run()

        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_07_unauthenticated_snapshot_rejected(self):
        run = self.create_report_run()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            },
        )

    def test_08_empty_list_returns_200(self):
        response = self.client.get(
            "/api/reporting/report-runs/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_09_list_response_is_list(self):
        response = self.client.get(
            "/api/reporting/report-runs/"
        )

        self.assertIsInstance(
            response.data,
            list,
        )

    def test_10_list_contains_created_run(self):
        run = self.create_report_run()

        response = self.client.get(
            "/api/reporting/report-runs/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run.id),
            ids,
        )


# ============================================================
# 11-25: CREATE / RETRIEVE TESTS
# ============================================================


class ReportRunCreateViewTests(
    BaseReportingViewTests,
):

    def test_11_create_report_run(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
                "metadata": {},
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            ReportRun.objects.filter(
                id=response.data["id"]
            ).exists()
        )

    def test_12_create_assigns_authenticated_user(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        run = ReportRun.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            run.created_by_id,
            self.user.id,
        )

    def test_13_create_initially_not_frozen(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertFalse(
            response.data["is_frozen"]
        )

    def test_14_create_initial_status_is_draft(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["status"],
            ReportRun.Status.DRAFT,
        )

    def test_15_create_metadata(self):
        metadata = {
            "source": "automated-test",
            "year": 2026,
        }

        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
                "metadata": metadata,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["metadata"],
            metadata,
        )

    def test_16_create_without_reporting_period_rejected(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_17_create_without_framework_version_rejected(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_18_create_invalid_reporting_period_rejected(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    uuid.uuid4()
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_19_create_invalid_framework_version_rejected(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    uuid.uuid4()
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_20_create_does_not_accept_created_by(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
                "created_by": self.normal_user.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        run = ReportRun.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            run.created_by_id,
            self.user.id,
        )

    def test_21_create_does_not_allow_status_override(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
                "status": ReportRun.Status.FROZEN,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["status"],
            ReportRun.Status.DRAFT,
        )

    def test_22_create_does_not_allow_frozen_timestamp(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
                "snapshot_frozen_at": (
                    "2026-08-22T10:00:00Z"
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertIsNone(
            response.data["snapshot_frozen_at"]
        )

    def test_23_create_with_second_period(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.second_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            str(response.data["reporting_period"]),
            str(self.second_period.id),
        )

    def test_24_create_with_second_framework_version(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.second_framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            str(response.data["framework_version"]),
            str(self.second_framework_version.id),
        )

    def test_25_create_response_contains_framework_metadata(self):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["framework_code"],
            self.framework.code,
        )

        self.assertEqual(
            response.data["framework_version_code"],
            self.framework_version.version_code,
        )


# ============================================================
# 26-38: DETAIL / PATCH / DELETE TESTS
# ============================================================


class ReportRunDetailViewTests(
    BaseReportingViewTests,
):

    def test_26_retrieve_report_run(self):
        run = self.create_report_run()

        response = self.client.get(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            str(response.data["id"]),
            str(run.id),
        )

    def test_27_retrieve_contains_reporting_period(self):
        run = self.create_report_run()

        response = self.client.get(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            str(response.data["reporting_period"]),
            str(self.reporting_period.id),
            )

    def test_28_retrieve_contains_framework_version(self):
        run = self.create_report_run()

        response = self.client.get(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            str(response.data["framework_version"]),
            str(self.framework_version.id),
            )

    def test_29_retrieve_contains_created_by(self):
        run = self.create_report_run()

        response = self.client.get(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            response.data["created_by"],
            self.user.id,
        )

    def test_30_retrieve_missing_run_returns_404(self):
        response = self.client.get(
            self.report_run_url(uuid.uuid4())
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_31_patch_unfrozen_metadata_allowed(self):
        run = self.create_report_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "metadata": {
                    "updated": True,
                }
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        run.refresh_from_db()

        self.assertEqual(
            run.metadata,
            {"updated": True},
        )

    def test_32_patch_unfrozen_reporting_period_allowed(self):
        run = self.create_report_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "reporting_period": str(
                    self.second_period.id
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_33_patch_unfrozen_framework_version_allowed(self):
        run = self.create_report_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "framework_version": str(
                    self.second_framework_version.id
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_34_delete_unfrozen_run(self):
        run = self.create_report_run()

        response = self.client.delete(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            ReportRun.objects.filter(
                id=run.id
            ).exists()
        )

    def test_35_delete_missing_run_returns_404(self):
        response = self.client.delete(
            self.report_run_url(uuid.uuid4())
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_36_patch_missing_run_returns_404(self):
        response = self.client.patch(
            self.report_run_url(uuid.uuid4()),
            {
                "metadata": {}
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_37_patch_invalid_period_returns_400(self):
        run = self.create_report_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "reporting_period": str(
                    uuid.uuid4()
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_38_patch_invalid_framework_version_returns_400(self):
        run = self.create_report_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "framework_version": str(
                    uuid.uuid4()
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# 39-47: FILTER TESTS
# ============================================================


class ReportRunFilterViewTests(
    BaseReportingViewTests,
):

    def test_39_filter_by_reporting_period(self):
        run_1 = self.create_report_run()

        run_2 = self.create_report_run(
            reporting_period=self.second_period
        )

        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                )
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run_1.id),
            ids,
        )

        self.assertNotIn(
            str(run_2.id),
            ids,
        )

    def test_40_filter_by_framework_version(self):
        run_1 = self.create_report_run()

        run_2 = self.create_report_run(
            framework_version=self.second_framework_version
        )

        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "framework_version": str(
                    self.framework_version.id
                )
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run_1.id),
            ids,
        )

        self.assertNotIn(
            str(run_2.id),
            ids,
        )

    def test_41_filter_by_draft_status(self):
        run = self.create_report_run()

        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "status": ReportRun.Status.DRAFT
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run.id),
            ids,
        )

    def test_42_filter_by_frozen_status(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "status": ReportRun.Status.FROZEN
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run.id),
            ids,
        )

    def test_43_invalid_reporting_period_filter_returns_empty(self):
        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    uuid.uuid4()
                )
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

    def test_44_invalid_framework_filter_returns_empty(self):
        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "framework_version": str(
                    uuid.uuid4()
                )
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

    def test_45_combined_period_and_framework_filter(self):
        run = self.create_report_run()

        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run.id),
            ids,
        )

    def test_46_filter_returns_only_matching_status(self):
        run_1 = self.create_report_run()
        run_2 = self.create_report_run()

        self.freeze_run(run_2)

        response = self.client.get(
            "/api/reporting/report-runs/",
            {
                "status": ReportRun.Status.DRAFT
            },
        )

        ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(run_1.id),
            ids,
        )

        self.assertNotIn(
            str(run_2.id),
            ids,
        )

    def test_47_list_order_is_newest_first(self):
        first = self.create_report_run()
        second = self.create_report_run()

        response = self.client.get(
            "/api/reporting/report-runs/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        ids = [
            str(item["id"])
            for item in response.data
        ]

        self.assertLess(
            ids.index(str(second.id)),
            ids.index(str(first.id)),
        )


# ============================================================
# 48-60: FREEZE VIEW TESTS
# ============================================================


class ReportRunFreezeViewTests(
    BaseReportingViewTests,
):

    def test_48_freeze_report_run_successfully(self):
        run = self.create_report_run()

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        run.refresh_from_db()

        self.assertTrue(
            run.is_frozen
        )

    def test_49_freeze_sets_frozen_status(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        run.refresh_from_db()

        self.assertEqual(
            run.status,
            ReportRun.Status.FROZEN,
        )

    def test_50_freeze_sets_snapshot_timestamp(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        run.refresh_from_db()

        self.assertIsNotNone(
            run.snapshot_frozen_at
        )

    def test_51_freeze_creates_framework_snapshot(self):
        run = self.create_report_run()

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            FrameworkSnapshot.objects.filter(
                report_run=run
            ).exists()
        )

    def test_52_freeze_copies_framework_code(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            snapshot.framework_code,
            self.framework.code,
        )

    def test_53_freeze_copies_framework_version_code(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            snapshot.version_code,
            self.framework_version.version_code,
        )

    def test_54_freeze_copies_all_framework_nodes(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            SnapshotNode.objects.filter(
                snapshot=snapshot
            ).count(),
            FrameworkNode.objects.filter(
                framework_version=self.framework_version
            ).count(),
        )

    def test_55_freeze_copies_mappings(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        self.assertEqual(
            SnapshotMapping.objects.filter(
                snapshot_node__snapshot=snapshot
            ).count(),
            DatapointMapping.objects.filter(
                framework_node__framework_version=self.framework_version
            ).count(),
        )

    def test_56_freeze_copies_canonical_datapoint_code(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot_mapping = (
            SnapshotMapping.objects.filter(
                snapshot_node__snapshot__report_run=run,
                source_mapping_id=self.mapping_1.id,
            ).first()
        )

        self.assertIsNotNone(
            snapshot_mapping
        )

        self.assertEqual(
            snapshot_mapping.canonical_datapoint_code,
            self.datapoint_1.code,
        )

    def test_57_freeze_copies_source_mapping_id(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot_mapping = (
            SnapshotMapping.objects.filter(
                snapshot_node__snapshot__report_run=run,
                source_mapping_id=self.mapping_1.id,
            ).first()
        )

        self.assertIsNotNone(
            snapshot_mapping
        )

        self.assertEqual(
            snapshot_mapping.source_mapping_id,
            self.mapping_1.id,
        )

    def test_58_freeze_builds_snapshot_parent_relationships(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        snapshot_child = SnapshotNode.objects.get(
            snapshot=snapshot,
            source_node_id=self.node_302_1.id,
        )

        snapshot_parent = SnapshotNode.objects.get(
            snapshot=snapshot,
            source_node_id=self.energy_subsection.id,
        )

        self.assertEqual(
            snapshot_child.parent_id,
            snapshot_parent.id,
        )

    def test_59_freeze_is_deterministically_ordered(self):
        run = self.create_report_run()

        self.client.post(
            self.freeze_url(run.id)
        )

        snapshot = FrameworkSnapshot.objects.get(
            report_run=run
        )

        nodes = list(
            SnapshotNode.objects.filter(
                snapshot=snapshot
            ).order_by(
                "path",
                "display_order",
                "code",
                "id",
            )
        )

        expected = sorted(
            nodes,
            key=lambda node: (
                node.path,
                node.display_order,
                node.code,
                str(node.id),
            ),
        )

        self.assertEqual(
            [node.id for node in nodes],
            [node.id for node in expected],
        )

    def test_60_freeze_response_contains_frozen_state(self):
        run = self.create_report_run()

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["is_frozen"]
        )


# ============================================================
# 61-67: RE-FREEZE / FROZEN PROTECTION
# ============================================================


class FrozenReportRunViewTests(
    BaseReportingViewTests,
):

    def create_frozen_run(self):
        run = self.create_report_run()

        self.freeze_run(run)

        run.refresh_from_db()

        return run

    def test_61_refreeze_is_rejected(self):
        run = self.create_frozen_run()

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_62_refreeze_does_not_create_second_snapshot(self):
        run = self.create_frozen_run()

        initial_count = FrameworkSnapshot.objects.filter(
            report_run=run
        ).count()

        self.client.post(
            self.freeze_url(run.id)
        )

        final_count = FrameworkSnapshot.objects.filter(
            report_run=run
        ).count()

        self.assertEqual(
            initial_count,
            1,
        )

        self.assertEqual(
            final_count,
            1,
        )

    def test_63_frozen_patch_is_rejected(self):
        run = self.create_frozen_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "metadata": {
                    "changed": True
                }
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_64_frozen_period_change_is_rejected(self):
        run = self.create_frozen_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "reporting_period": str(
                    self.second_period.id
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_65_frozen_framework_change_is_rejected(self):
        run = self.create_frozen_run()

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "framework_version": str(
                    self.second_framework_version.id
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_66_frozen_delete_is_rejected(self):
        run = self.create_frozen_run()

        response = self.client.delete(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            ReportRun.objects.filter(
                id=run.id
            ).exists()
        )

    def test_67_frozen_detail_remains_retrievable(self):
        run = self.create_frozen_run()

        response = self.client.get(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["is_frozen"]
        )


# ============================================================
# 68-75: SNAPSHOT API TESTS
# ============================================================


class ReportRunSnapshotViewTests(
    BaseReportingViewTests,
):

    def test_68_snapshot_for_frozen_run_returns_200(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_69_snapshot_contains_report_run_id(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            response.data["report_run_id"],
            str(run.id),
        )

    def test_70_snapshot_contains_framework_code(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            response.data["framework_code"],
            self.framework.code,
        )

    def test_71_snapshot_contains_framework_version_code(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            response.data["version_code"],
            self.framework_version.version_code,
        )

    def test_72_snapshot_contains_all_nodes(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            len(response.data["nodes"]),
            FrameworkNode.objects.filter(
                framework_version=self.framework_version
            ).count(),
        )

    def test_73_snapshot_contains_nested_mappings(self):
        run = self.create_report_run()

        self.freeze_run(run)

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        mapping_count = sum(
            len(node["mappings"])
            for node in response.data["nodes"]
        )

        self.assertEqual(
            mapping_count,
            2,
        )

    def test_74_snapshot_for_unfrozen_run_returns_404(self):
        run = self.create_report_run()

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_75_snapshot_for_missing_run_returns_404(self):
        response = self.client.get(
            self.snapshot_url(uuid.uuid4())
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


# ============================================================
# 76-82: SNAPSHOT IMMUTABILITY / HISTORICAL ISOLATION
# ============================================================


class SnapshotHistoricalIsolationTests(
    BaseReportingViewTests,
):

    def test_76_live_node_title_change_does_not_change_snapshot(self):
        run = self.create_report_run()

        self.freeze_run(run)

        snapshot_node = SnapshotNode.objects.get(
            snapshot__report_run=run,
            source_node_id=self.node_302_1.id,
        )

        original_title = snapshot_node.title

        self.node_302_1.title = (
            "CHANGED LIVE M7 TITLE"
        )
        self.node_302_1.save()

        snapshot_node.refresh_from_db()

        self.assertEqual(
            snapshot_node.title,
            original_title,
        )

    def test_77_live_node_order_change_does_not_change_snapshot(self):
        run = self.create_report_run()

        self.freeze_run(run)

        snapshot_node = SnapshotNode.objects.get(
            snapshot__report_run=run,
            source_node_id=self.node_302_1.id,
        )

        original_order = snapshot_node.display_order

        self.node_302_1.display_order = (
            original_order + 100
        )
        self.node_302_1.save()

        snapshot_node.refresh_from_db()

        self.assertEqual(
            snapshot_node.display_order,
            original_order,
        )

    def test_78_live_mapping_note_change_does_not_change_snapshot(self):
        run = self.create_report_run()

        self.freeze_run(run)

        snapshot_mapping = SnapshotMapping.objects.get(
            snapshot_node__snapshot__report_run=run,
            source_mapping_id=self.mapping_1.id,
        )

        original_note = snapshot_mapping.mapping_note

        self.mapping_1.mapping_note = (
            "CHANGED LIVE M7 NOTE"
        )
        self.mapping_1.save()

        snapshot_mapping.refresh_from_db()

        self.assertEqual(
            snapshot_mapping.mapping_note,
            original_note,
        )

    def test_79_live_mapping_primary_change_does_not_change_snapshot(self):
        run = self.create_report_run()

        self.freeze_run(run)

        snapshot_mapping = SnapshotMapping.objects.get(
            snapshot_node__snapshot__report_run=run,
            source_mapping_id=self.mapping_1.id,
        )

        original_primary = snapshot_mapping.is_primary

        self.mapping_1.is_primary = False
        self.mapping_1.save()

        snapshot_mapping.refresh_from_db()

        self.assertEqual(
            snapshot_mapping.is_primary,
            original_primary,
        )

    def test_80_live_datapoint_code_change_does_not_change_snapshot(self):
        run = self.create_report_run()

        self.freeze_run(run)

        snapshot_mapping = SnapshotMapping.objects.get(
            snapshot_node__snapshot__report_run=run,
            source_mapping_id=self.mapping_1.id,
        )

        original_code = (
            snapshot_mapping.canonical_datapoint_code
        )

        self.datapoint_1.code = (
            "CHANGED_DATAPOINT_CODE"
        )
        self.datapoint_1.save()

        snapshot_mapping.refresh_from_db()

        self.assertEqual(
            snapshot_mapping.canonical_datapoint_code,
            original_code,
        )

    def test_81_snapshot_api_remains_unchanged_after_live_node_edit(self):
        run = self.create_report_run()

        self.freeze_run(run)

        before = self.client.get(
            self.snapshot_url(run.id)
        )

        original_node = next(
            node
            for node in before.data["nodes"]
            if node["source_node_id"]
            == str(self.node_302_1.id)
        )

        self.node_302_1.title = "LIVE EDIT"
        self.node_302_1.save()

        after = self.client.get(
            self.snapshot_url(run.id)
        )

        changed_node = next(
            node
            for node in after.data["nodes"]
            if node["source_node_id"]
            == str(self.node_302_1.id)
        )

        self.assertEqual(
            changed_node["title"],
            original_node["title"],
        )

    def test_82_snapshot_is_still_available_after_live_mapping_edit(self):
        run = self.create_report_run()

        self.freeze_run(run)

        self.mapping_1.mapping_note = (
            "LIVE M7 CHANGE"
        )
        self.mapping_1.save()

        response = self.client.get(
            self.snapshot_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mappings = [
            mapping
            for node in response.data["nodes"]
            for mapping in node["mappings"]
        ]

        self.assertTrue(
            any(
                mapping["source_mapping_id"]
                == str(self.mapping_1.id)
                for mapping in mappings
            )
        )


# ============================================================
# 83-88: RBAC WRITE TESTS
# ============================================================


class ReportRunRBACViewTests(
    BaseReportingViewTests,
):

    def setUp(self):
        self.client.force_authenticate(
            user=self.normal_user
        )

    @patch(
        "apps.accounts.permissions."
        "HasRolePermission.has_permission",
        return_value=False,
    )
    def test_83_rbac_denies_create(
        self,
        mock_permission,
    ):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @patch(
        "apps.accounts.permissions."
        "HasRolePermission.has_permission",
        return_value=False,
    )
    def test_84_rbac_denies_update(
        self,
        mock_permission,
    ):
        run = self.create_report_run(
            created_by=self.normal_user
        )

        response = self.client.patch(
            self.report_run_url(run.id),
            {
                "metadata": {
                    "attempt": "denied"
                }
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @patch(
        "apps.accounts.permissions."
        "HasRolePermission.has_permission",
        return_value=False,
    )
    def test_85_rbac_denies_delete(
        self,
        mock_permission,
    ):
        run = self.create_report_run(
            created_by=self.normal_user
        )

        response = self.client.delete(
            self.report_run_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @patch(
        "apps.accounts.permissions."
        "HasRolePermission.has_permission",
        return_value=False,
    )
    def test_86_rbac_denies_freeze(
        self,
        mock_permission,
    ):
        run = self.create_report_run(
            created_by=self.normal_user
        )

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @patch(
        "apps.accounts.permissions."
        "HasRolePermission.has_permission",
        return_value=True,
    )
    def test_87_rbac_allows_create(
        self,
        mock_permission,
    ):
        response = self.client.post(
            "/api/reporting/report-runs/",
            {
                "reporting_period": str(
                    self.reporting_period.id
                ),
                "framework_version": str(
                    self.framework_version.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    @patch(
        "apps.accounts.permissions."
        "HasRolePermission.has_permission",
        return_value=True,
    )
    def test_88_rbac_allows_freeze(
        self,
        mock_permission,
    ):
        run = self.create_report_run(
            created_by=self.normal_user
        )

        response = self.client.post(
            self.freeze_url(run.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )