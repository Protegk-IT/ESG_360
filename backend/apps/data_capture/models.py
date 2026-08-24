"""Generic, M4-driven data-capture persistence models.

Definitions belong to ``apps.datapoints``.  This app stores only the request,
captured values, attached evidence, and the durable workflow record.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import ActivityLogMixin
from apps.core.models import BaseModel
from apps.datapoints.models import DatapointDataType
from apps.data_capture.validation import validate_typed_value


class DataRequestStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class SubmissionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class CollectionCampaignStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"


def _submission_is_editable(submission_id):
    """Read the persisted status instead of trusting a stale related cache."""

    return Submission.objects.filter(
        pk=submission_id, status=SubmissionStatus.DRAFT
    ).exists()


class DataRequest(ActivityLogMixin, BaseModel):
    """A canonical datapoint owed for one organisation and reporting period."""

    datapoint = models.ForeignKey(
        "datapoints.Datapoint", on_delete=models.PROTECT, related_name="data_requests"
    )
    org_node = models.ForeignKey(
        "organizations.OrgNode", on_delete=models.PROTECT, related_name="data_requests"
    )
    reporting_period = models.ForeignKey(
        "periods.ReportingPeriod", on_delete=models.PROTECT, related_name="data_requests"
    )
    module_code = models.CharField(max_length=100, editable=False)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_data_requests"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_data_requests"
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=DataRequestStatus.choices, default=DataRequestStatus.OPEN
    )
    instructions = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["due_date", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "org_node", "reporting_period"],
                name="uq_data_request_datapoint_org_period",
            ),
        ]
        indexes = [
            models.Index(fields=["assignee", "status"]),
            models.Index(fields=["org_node", "reporting_period"]),
            models.Index(fields=["module_code"]),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.datapoint_id:
            canonical_module = self.datapoint.module_id
            if self.module_code and self.module_code != canonical_module:
                errors["module_code"] = "Module code must match the datapoint module."
            self.module_code = canonical_module
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous = type(self).objects.filter(pk=self.pk).values("status", "assignee_id").first()
            if (
                previous
                and previous["status"] != self.status
                and not getattr(self, "_allow_lifecycle_transition", False)
            ):
                raise ValidationError(
                    "Data-request status transitions must use DataCaptureLifecycleService."
                )
            if (
                previous
                and previous["assignee_id"] != self.assignee_id
                and not getattr(self, "_allow_reassignment", False)
            ):
                raise ValidationError(
                    "Data-request reassignment must use DataCaptureLifecycleService."
                )
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.datapoint.code} for {self.org_node}"


class CollectionCampaign(ActivityLogMixin, BaseModel):
    """Manager-owned orchestration metadata for normal M5 data requests.

    A campaign never owns answer or review state.  Its explicit targets link
    to the existing ``DataRequest`` records that remain the workflow source of
    truth.
    """

    company = models.ForeignKey(
        "companies.Company", on_delete=models.PROTECT, related_name="collection_campaigns"
    )
    reporting_period = models.ForeignKey(
        "periods.ReportingPeriod", on_delete=models.PROTECT, related_name="collection_campaigns"
    )
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    default_due_date = models.DateField(null=True, blank=True)
    default_instructions = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=CollectionCampaignStatus.choices,
        default=CollectionCampaignStatus.DRAFT,
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_collection_campaigns"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "reporting_period"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous_status = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            if (
                previous_status
                and previous_status != self.status
                and not getattr(self, "_allow_campaign_transition", False)
            ):
                raise ValidationError(
                    "Collection-campaign status transitions must use CollectionCampaignService."
                )
        self.full_clean()
        super().save(*args, **kwargs)


class CampaignTarget(BaseModel):
    """One explicit datapoint × OrgNode orchestration target.

    ``data_request`` may point at a pre-existing equivalent request.  The
    intended values are retained for traceability, but generation never edits
    a linked request; reassignment stays an explicit lifecycle operation.
    """

    class RequestOutcome(models.TextChoices):
        CREATED = "CREATED", "Created"
        EXISTING = "EXISTING", "Existing/reused"

    campaign = models.ForeignKey(
        CollectionCampaign, on_delete=models.CASCADE, related_name="targets"
    )
    datapoint = models.ForeignKey(
        "datapoints.Datapoint", on_delete=models.PROTECT, related_name="campaign_targets"
    )
    org_node = models.ForeignKey(
        "organizations.OrgNode", on_delete=models.PROTECT, related_name="campaign_targets"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="campaign_targets"
    )
    due_date = models.DateField(null=True, blank=True)
    instructions = models.TextField(blank=True, default="")
    data_request = models.ForeignKey(
        DataRequest, on_delete=models.PROTECT, null=True, blank=True,
        related_name="campaign_targets",
    )
    request_outcome = models.CharField(
        max_length=20, choices=RequestOutcome.choices, blank=True, default=""
    )

    class Meta:
        ordering = ["datapoint__code", "org_node__path"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "datapoint", "org_node"],
                name="uq_campaign_target_datapoint_org",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "org_node"]),
            models.Index(fields=["data_request"]),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.campaign_id and self.org_node_id and self.org_node.company_id != self.campaign.company_id:
            errors["org_node"] = "Campaign targets must belong to the campaign company."
        if self.data_request_id:
            request = self.data_request
            if request.datapoint_id != self.datapoint_id:
                errors["data_request"] = "Linked request must use this target's datapoint."
            if request.org_node_id != self.org_node_id:
                errors["data_request"] = "Linked request must use this target's OrgNode."
            if request.reporting_period_id != self.campaign.reporting_period_id:
                errors["data_request"] = "Linked request must use the campaign reporting period."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous = type(self).objects.filter(pk=self.pk).values(
                "data_request_id", "assignee_id", "due_date", "instructions"
            ).first()
            if (
                previous
                and previous["data_request_id"]
                and any(
                    previous[field] != getattr(self, field)
                    for field in ("assignee_id", "due_date", "instructions")
                )
                and not getattr(self, "_allow_target_update", False)
            ):
                raise ValidationError(
                    "Generated campaign targets must be changed through CollectionCampaignService."
                )
        self.full_clean()
        super().save(*args, **kwargs)


class CollectionCampaignEvent(BaseModel):
    """Append-only campaign operation history; request events remain separate."""

    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        GENERATED = "GENERATED", "Requests generated"
        REASSIGNED = "REASSIGNED", "Requests reassigned"
        CLOSED = "CLOSED", "Closed"

    campaign = models.ForeignKey(
        CollectionCampaign, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Collection-campaign history is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Collection-campaign history is immutable.")


class DataRequestEvent(BaseModel):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        ASSIGNED = "ASSIGNED", "Assigned"
        REASSIGNED = "REASSIGNED", "Reassigned"
        CANCELLED = "CANCELLED", "Cancelled"

    data_request = models.ForeignKey(
        DataRequest, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    previous_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="previous_data_request_events",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="data_request_events",
    )
    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Data-request history is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Data-request history is immutable.")


class Submission(ActivityLogMixin, BaseModel):
    """The current, auditable submission workflow for a data request."""

    data_request = models.OneToOneField(
        DataRequest, on_delete=models.PROTECT, related_name="submission"
    )
    status = models.CharField(
        max_length=20, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submitted_data_capture_submissions",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_data_capture_submissions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_data_capture_submissions",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reopened_data_capture_submissions",
    )

    class Meta:
        indexes = [models.Index(fields=["status"])]

    @property
    def datapoint(self):
        return self.data_request.datapoint

    @property
    def org_node(self):
        return self.data_request.org_node

    @property
    def reporting_period(self):
        return self.data_request.reporting_period

    def clean(self):
        super().clean()
        if self.status == SubmissionStatus.REJECTED and not self.rejection_reason.strip():
            raise ValidationError({"rejection_reason": "Rejected submissions require a reason."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous_status = (
                type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )
            if (
                previous_status
                and previous_status != self.status
                and not getattr(self, "_allow_lifecycle_transition", False)
            ):
                raise ValidationError(
                    "Submission status transitions must use DataCaptureLifecycleService."
                )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Submissions are historical records and cannot be deleted.")


class SubmissionEvent(BaseModel):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        DRAFT_SAVED = "DRAFT_SAVED", "Draft saved"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REOPENED = "REOPENED", "Reopened"

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    from_status = models.CharField(max_length=20, choices=SubmissionStatus.choices, blank=True, default="")
    to_status = models.CharField(max_length=20, choices=SubmissionStatus.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Submission history is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Submission history is immutable.")


class Answer(ActivityLogMixin, BaseModel):
    """One typed scalar or TABLE answer for a submission's canonical datapoint."""

    submission = models.OneToOneField(
        Submission, on_delete=models.CASCADE, related_name="answer"
    )
    decimal_value = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    integer_value = models.BigIntegerField(null=True, blank=True)
    text_value = models.TextField(blank=True, default="")
    boolean_value = models.BooleanField(null=True, blank=True)
    selected_option = models.ForeignKey(
        "datapoints.DatapointOption", on_delete=models.PROTECT, null=True, blank=True
    )
    date_value = models.DateField(null=True, blank=True)
    unit = models.ForeignKey("datapoints.Unit", on_delete=models.PROTECT, null=True, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="entered_data_capture_answers"
    )

    class Meta:
        indexes = [
            models.Index(fields=["decimal_value"]),
            models.Index(fields=["integer_value"]),
            models.Index(fields=["date_value"]),
            models.Index(fields=["selected_option"]),
        ]

    @property
    def datapoint(self):
        return self.submission.data_request.datapoint

    def clean(self):
        super().clean()
        if self.submission_id:
            validate_typed_value(self, definition=self.datapoint)

    def save(self, *args, **kwargs):
        if not self._state.adding and not _submission_is_editable(self.submission_id):
            raise ValidationError("Answers may only be changed in an editable draft submission.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Answers must be changed through the data-capture draft workflow.")


class AnswerTableRow(ActivityLogMixin, BaseModel):
    """A fixed M4 row or a user-added dynamic row belonging to a TABLE answer."""

    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="table_rows")
    definition_row = models.ForeignKey(
        "datapoints.DatapointTableRow", on_delete=models.PROTECT, null=True, blank=True
    )
    label = models.CharField(max_length=255, blank=True, default="")
    display_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["display_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "definition_row"],
                condition=models.Q(definition_row__isnull=False),
                name="uq_answer_table_fixed_row",
            ),
            models.UniqueConstraint(
                fields=["answer", "display_order"],
                name="uq_answer_table_row_order",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.answer_id:
            return
        datapoint = self.answer.datapoint
        errors = {}
        if datapoint.data_type != DatapointDataType.TABLE:
            errors["answer"] = "Table rows require a TABLE answer."
        if self.definition_row_id:
            if self.definition_row.datapoint_id != datapoint.id:
                errors["definition_row"] = "Fixed row does not belong to this TABLE definition."
            if self.label and self.label != self.definition_row.label:
                errors["label"] = "Fixed rows use the canonical row label."
            self.label = self.definition_row.label
            self.display_order = self.definition_row.display_order
        elif not datapoint.allow_dynamic_rows:
            errors["definition_row"] = "This TABLE only allows its fixed catalog rows."
        elif not self.label.strip():
            errors["label"] = "Dynamic rows require a label."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self._state.adding and not Submission.objects.filter(
            answer__pk=self.answer_id, status=SubmissionStatus.DRAFT
        ).exists():
            raise ValidationError("TABLE rows may only be changed in an editable draft submission.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("TABLE rows must be changed through the data-capture draft workflow.")


class AnswerTableCell(ActivityLogMixin, BaseModel):
    """One typed, queryable cell linked to an M4 TABLE column definition."""

    row = models.ForeignKey(AnswerTableRow, on_delete=models.CASCADE, related_name="cells")
    column = models.ForeignKey("datapoints.DatapointTableColumn", on_delete=models.PROTECT)
    decimal_value = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    integer_value = models.BigIntegerField(null=True, blank=True)
    text_value = models.TextField(blank=True, default="")
    boolean_value = models.BooleanField(null=True, blank=True)
    selected_option = models.ForeignKey(
        "datapoints.DatapointOption", on_delete=models.PROTECT, null=True, blank=True
    )
    date_value = models.DateField(null=True, blank=True)
    unit = models.ForeignKey("datapoints.Unit", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["row", "column"], name="uq_answer_table_cell"),
        ]
        indexes = [
            models.Index(fields=["decimal_value"]),
            models.Index(fields=["integer_value"]),
            models.Index(fields=["date_value"]),
        ]

    def clean(self):
        super().clean()
        if not self.row_id or not self.column_id:
            return
        datapoint = self.row.answer.datapoint
        if self.column.datapoint_id != datapoint.id:
            raise ValidationError({"column": "Column does not belong to this TABLE definition."})
        validate_typed_value(self, definition=self.column, field_name="column")

    def save(self, *args, **kwargs):
        if not self._state.adding and not Submission.objects.filter(
            answer__table_rows__pk=self.row_id, status=SubmissionStatus.DRAFT
        ).exists():
            raise ValidationError("TABLE cells may only be changed in an editable draft submission.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("TABLE cells must be changed through the data-capture draft workflow.")


class EvidenceFile(ActivityLogMixin, BaseModel):
    """Storage-backed evidence attached to a submission or one of its answers."""

    MAX_FILE_SIZE = 10 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="evidence_files"
    )
    answer = models.ForeignKey(
        Answer, on_delete=models.PROTECT, related_name="evidence_files", null=True, blank=True
    )
    file = models.FileField(upload_to="data_capture/evidence/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_data_capture_evidence"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["submission"])]

    def clean(self):
        super().clean()
        errors = {}
        if self.answer_id and self.answer.submission_id != self.submission_id:
            errors["answer"] = "Evidence answer must belong to the selected submission."
        if self.submission_id and self.submission.status != SubmissionStatus.DRAFT:
            errors["submission"] = "Evidence may only be added to an editable draft submission."
        if self.content_type not in self.ALLOWED_CONTENT_TYPES:
            errors["content_type"] = "Unsupported evidence file type."
        file_size = self.file.size if self.file else self.size
        if file_size > self.MAX_FILE_SIZE:
            errors["size"] = "Evidence files must not exceed 10 MB."
        if self.size != file_size:
            self.size = file_size
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not getattr(self, "_allow_service_delete", False):
            raise ValidationError("Evidence deletion must use the data-capture evidence service.")
        if not _submission_is_editable(self.submission_id):
            raise ValidationError("Evidence may only be deleted from an editable draft submission.")
        storage = self.file.storage if self.file else None
        name = self.file.name if self.file else ""
        result = super().delete(*args, **kwargs)
        if storage and name:
            from django.db import transaction

            transaction.on_commit(lambda: storage.delete(name))
        return result
