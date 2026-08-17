import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class ImportBatch(BaseModel):
    class ImportType(models.TextChoices):
        ANSWERS = "ANSWERS", "Answers"
        DATAPOINTS = "DATAPOINTS", "Datapoints"
        FRAMEWORK_NODES = "FRAMEWORK_NODES", "Framework Nodes"
        STAKEHOLDERS = "STAKEHOLDERS", "Stakeholders"
        EMISSION_FACTORS = "EMISSION_FACTORS", "Emission Factors"

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        VALIDATING = "VALIDATING", "Validating"
        VALIDATED = "VALIDATED", "Validated"
        FAILED = "FAILED", "Failed"
        COMMITTED = "COMMITTED", "Committed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    import_type = models.CharField(
        max_length=50,
        choices=ImportType.choices,
    )

    file_name = models.CharField(
        max_length=255,
    )

    file_path = models.CharField(
        max_length=500,
    )

    org_node = models.ForeignKey(
        "organizations.OrgNode",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="import_batches",
    )

    reporting_period = models.ForeignKey(
        "periods.ReportingPeriod",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="import_batches",
    )

    module_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    committed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def clean(self):
        super().clean()

        if self.status == self.Status.COMMITTED and not self.committed_at:
            raise ValidationError(
                {"committed_at": "Committed batches must have committed_at set."}
            )

    def __str__(self):
        return f"{self.file_name} ({self.import_type})"


class ImportRow(BaseModel):
    class Status(models.TextChoices):
        VALID = "VALID", "Valid"
        ERROR = "ERROR", "Error"
        SKIPPED = "SKIPPED", "Skipped"
        COMMITTED = "COMMITTED", "Committed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="rows",
    )

    row_number = models.PositiveIntegerField()

    raw_data = models.JSONField(
        default=dict,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VALID,
    )

    errors = models.JSONField(
        default=dict,
        blank=True,
    )

    def __str__(self):
        return f"Batch {self.batch_id} - Row {self.row_number}"