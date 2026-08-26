from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.periods.models import ReportingPeriod
from apps.frameworks.models import FrameworkVersion


class ReportRun(BaseModel):
    """
    M8 reporting execution context.

    A ReportRun identifies:

        ReportingPeriod
              +
        FrameworkVersion
              +
        User who created/requested the run

    M5 Answer/Submission/DataRequest and M6 calculated-result
    models are intentionally NOT referenced here.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FROZEN = "FROZEN", "Frozen"

    # ------------------------------------------------------------------
    # REPORTING CONTEXT
    # ------------------------------------------------------------------

    reporting_period = models.ForeignKey(
        ReportingPeriod,
        on_delete=models.PROTECT,
        related_name="report_runs",
    )

    # Reporting periods are global, whereas captured values belong to an
    # OrgNode and therefore a company.  Keep legacy rows nullable, but never
    # resolve them without an explicit scope.
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="report_runs",
        null=True,
        blank=True,
    )

    framework_version = models.ForeignKey(
        FrameworkVersion,
        on_delete=models.PROTECT,
        related_name="report_runs",
    )

    # ------------------------------------------------------------------
    # BUSINESS ACTOR
    # ------------------------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_report_runs",
    )

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    snapshot_frozen_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Stable run-level metadata.
    #
    # This must NOT be used for:
    # - M5 answers
    # - M5 submissions
    # - M5 data requests
    # - M6 calculated results
    #
    # Those belong to later integration work.
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "report_runs"

        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["reporting_period"],
                name="idx_report_run_period",
            ),
            models.Index(
                fields=["framework_version"],
                name="idx_report_run_fw_version",
            ),
            models.Index(
                fields=["status"],
                name="idx_report_run_status",
            ),
            models.Index(fields=["company"], name="idx_report_run_company"),
        ]

    def __str__(self):
        return (
            f"{self.framework_version} - "
            f"{self.reporting_period}"
        )

    @property
    def is_frozen(self):
        """
        Convenience property used by services, views and tests.
        """
        return self.status == self.Status.FROZEN

    def clean(self):
        """
        Protect the reporting context after freezing.

        Once a ReportRun is frozen:

        - reporting_period cannot change;
        - framework_version cannot change;
        - status cannot move away from FROZEN.

        The DRAFT -> FROZEN transition is controlled by the
        M8 freeze service.
        """

        super().clean()

        if not self.pk:
            return

        try:
            previous = type(self).objects.get(pk=self.pk)
        except type(self).DoesNotExist:
            return

        if previous.status == self.Status.FROZEN:

            if (
                previous.reporting_period_id
                != self.reporting_period_id
            ):
                raise ValidationError(
                    {
                        "reporting_period": (
                            "Reporting period cannot be changed "
                            "after the report run is frozen."
                        )
                    }
                )

            if (
                previous.framework_version_id
                != self.framework_version_id
            ):
                raise ValidationError(
                    {
                        "framework_version": (
                            "Framework version cannot be changed "
                            "after the report run is frozen."
                        )
                    }
                )

            if previous.company_id != self.company_id:
                raise ValidationError(
                    {"company": "Company cannot be changed after the report run is frozen."}
                )

            if self.status != self.Status.FROZEN:
                raise ValidationError(
                    {
                        "status": (
                            "A frozen report run cannot be "
                            "moved back to another lifecycle state."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        """
        Apply model validation before persistence.
        """
        self.full_clean()
        return super().save(*args, **kwargs)


class FrameworkSnapshot(BaseModel):
    """
    Immutable historical copy of the selected M7 FrameworkVersion.

    During freeze:

        M7 FrameworkVersion
                |
                | copy
                v
        M8 FrameworkSnapshot

    The snapshot stores the framework/version identity and becomes
    the historical source of truth for the report run.

    It deliberately does not depend on mutable M7 rows after freeze.
    """

    report_run = models.OneToOneField(
        ReportRun,
        on_delete=models.PROTECT,
        related_name="framework_snapshot",
    )

    # ------------------------------------------------------------------
    # ORIGINAL M7 FRAMEWORK IDENTITY
    # ------------------------------------------------------------------

    # Copied identifiers for traceability.
    #
    # These are UUID values rather than ForeignKeys because the
    # historical snapshot must not rely on mutable M7 records.

    source_framework_id = models.UUIDField()

    source_framework_version_id = models.UUIDField()

    framework_code = models.CharField(
        max_length=50,
    )

    framework_name = models.CharField(
        max_length=255,
    )

    version_code = models.CharField(
        max_length=100,
    )

    version_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    frozen_at = models.DateTimeField()

    class Meta:
        db_table = "framework_snapshots"

    def __str__(self):
        return (
            f"{self.framework_code} "
            f"{self.version_code} snapshot"
        )

    def save(self, *args, **kwargs):
        """
        FrameworkSnapshot is immutable after initial creation.

        IMPORTANT:
        BaseModel generates UUID primary keys before the first
        database save. Therefore self.pk cannot be used to determine
        whether this is an INSERT or UPDATE.

        Django's _state.adding correctly identifies the initial INSERT.
        """

        if not self._state.adding:
            raise ValidationError(
                "Framework snapshots are immutable and "
                "cannot be updated."
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Historical framework snapshots cannot be deleted through
        normal model operations.
        """
        raise ValidationError(
            "Framework snapshots are immutable and "
            "cannot be deleted."
        )


class SnapshotNode(BaseModel):
    """
    Immutable historical copy of an M7 FrameworkNode.

    The original M7 node ID is retained for traceability.

    Parent-child relationships are recreated using SnapshotNode
    itself so the historical tree remains independent from the
    live M7 FrameworkNode hierarchy.
    """

    snapshot = models.ForeignKey(
        FrameworkSnapshot,
        on_delete=models.PROTECT,
        related_name="nodes",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )

    # Original M7 FrameworkNode ID.
    # Traceability only.
    source_node_id = models.UUIDField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # COPIED M7 FRAMEWORK NODE DATA
    # ------------------------------------------------------------------

    code = models.CharField(
        max_length=150,
    )

    title = models.CharField(
        max_length=500,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    instructions = models.TextField(
        blank=True,
        default="",
    )

    node_type = models.CharField(
        max_length=30,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    depth = models.PositiveIntegerField(
        default=0,
    )

    path = models.TextField(
        blank=True,
        default="",
    )

    response_format = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    is_answerable = models.BooleanField(
        default=False,
    )

    is_core = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    # Additional reporting-relevant M7 metadata.
    #
    # Do NOT use this for M5 answers or M6 calculated values.
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "report_snapshot_nodes"

        # Deterministic snapshot ordering.
        ordering = [
            "path",
            "display_order",
            "code",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "snapshot",
                    "code",
                ],
                name="uq_snapshot_node_code",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "snapshot",
                    "parent",
                ],
                name="idx_snapshot_node_parent",
            ),
            models.Index(
                fields=[
                    "snapshot",
                    "path",
                ],
                name="idx_snapshot_node_path",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"

    def save(self, *args, **kwargs):
        """
        Snapshot nodes are created by the freeze service only.

        Existing snapshot nodes cannot be updated.

        _state.adding is used instead of self.pk because BaseModel
        assigns the UUID before the first database INSERT.
        """

        if not self._state.adding:
            raise ValidationError(
                "Snapshot nodes are immutable and "
                "cannot be updated."
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Snapshot nodes cannot be deleted through normal model
        operations.
        """
        raise ValidationError(
            "Snapshot nodes are immutable and "
            "cannot be deleted."
        )


class SnapshotMapping(BaseModel):
    """
    Immutable historical copy of an M7 DatapointMapping.

    Stores the canonical M4 Datapoint identity required by the
    future M5/M6 value-resolution layer.

    This model does NOT store:

        - M5 answers
        - M5 submissions
        - M5 data requests
        - M6 calculated results
        - resolved report values

    Those belong to later integration work.
    """

    snapshot_node = models.ForeignKey(
        SnapshotNode,
        on_delete=models.PROTECT,
        related_name="mappings",
    )

    # ------------------------------------------------------------------
    # ORIGINAL M7 / M4 IDENTITIES
    # ------------------------------------------------------------------

    # Original M7 DatapointMapping ID.
    # Traceability only.
    source_mapping_id = models.UUIDField(
        null=True,
        blank=True,
    )

    # Original M4 Datapoint ID.
    # Traceability only.
    source_datapoint_id = models.UUIDField(
        null=True,
        blank=True,
    )

    # Stable canonical M4 datapoint code.
    #
    # This is the important future integration key.
    canonical_datapoint_code = models.CharField(
        max_length=255,
    )

    # ------------------------------------------------------------------
    # COPIED M7 MAPPING DATA
    # ------------------------------------------------------------------

    mapping_type = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    aggregation = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    transform_expression = models.TextField(
        blank=True,
        default="",
    )

    is_primary = models.BooleanField(
        default=False,
    )

    confidence = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    mapping_note = models.TextField(
        blank=True,
        default="",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # M7 DatapointMapping does not provide display_order.
    #
    # M8 therefore stores its own deterministic ordering value
    # generated by the freeze service.
    display_order = models.PositiveIntegerField(
        default=0,
    )

    # Additional mapping metadata.
    #
    # Do NOT use this for M5 answers or M6 calculated values.
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "report_snapshot_mappings"

        # Deterministic mapping ordering.
        ordering = [
            "snapshot_node",
            "display_order",
            "canonical_datapoint_code",
            "id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "snapshot_node",
                ],
                name="idx_snapshot_mapping_node",
            ),
            models.Index(
                fields=[
                    "canonical_datapoint_code",
                ],
                name="idx_snapshot_mapping_dp_code",
            ),
        ]

    def __str__(self):
        return (
            f"{self.snapshot_node.code} -> "
            f"{self.canonical_datapoint_code}"
        )

    def save(self, *args, **kwargs):
        """
        Snapshot mappings are created by the freeze service only.

        Existing snapshot mappings cannot be updated.

        _state.adding is used instead of self.pk because BaseModel
        assigns the UUID before the first database INSERT.
        """

        if not self._state.adding:
            raise ValidationError(
                "Snapshot mappings are immutable and "
                "cannot be updated."
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Snapshot mappings cannot be deleted through normal model
        operations.
        """
        raise ValidationError(
            "Snapshot mappings are immutable and "
            "cannot be deleted."
        )
