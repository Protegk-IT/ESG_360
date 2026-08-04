from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
import uuid
from django.utils import timezone


class PeriodType(models.TextChoices):
    ANNUAL = "ANNUAL", "Annual"
    HALF_YEARLY = "HALF_YEARLY", "Half Yearly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    MONTHLY = "MONTHLY", "Monthly"


class Status(models.TextChoices):
    OPEN = "OPEN", "Open"
    LOCKED = "LOCKED", "Locked"
    CLOSED = "CLOSED", "Closed"


class ReportingPeriod(models.Model):
    """
    ReportingPeriod model representing hierarchical reporting periods.

    Validations implemented in clean():
    - end_date must be after start_date.
    - Annual periods must not overlap (prevents two ANNUAL periods with overlapping date ranges).
    - If parent is set, the child's start_date/end_date must be within the parent's date range.
    - Only one ReportingPeriod can have is_baseline_year=True (global constraint enforced at model validation time).
    - CLOSED is terminal: once a period is CLOSED it cannot be moved back to OPEN or LOCKED.

    The model calls full_clean() inside save() so database writes respect the validations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    name = models.CharField(max_length=255)
    period_type = models.CharField(max_length=20, choices=PeriodType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    is_baseline_year = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="locked_periods")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["period_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["is_baseline_year"]),
            models.Index(fields=["parent"]),
        ]

    def clean(self):
        errors = {}

        # 1) end_date must be greater than start_date
        if self.end_date <= self.start_date:
            errors["end_date"] = "end_date must be after start_date."

        # 2) If parent provided, child must fall completely inside parent period
        if self.parent:
            parent = self.parent
            if parent.start_date and self.start_date < parent.start_date:
                errors["start_date"] = "Child period start_date must not be before parent.start_date."
            if parent.end_date and self.end_date > parent.end_date:
                errors["end_date"] = "Child period end_date must not be after parent.end_date."

        # 3) Annual periods must not overlap with other ANNUAL periods
        #    Overlap definition: two periods overlap if their date ranges intersect.
        if self.period_type == PeriodType.ANNUAL:
            qs = ReportingPeriod.objects.filter(period_type=PeriodType.ANNUAL, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            overlap_exists = qs.filter(start_date__lte=self.end_date, end_date__gte=self.start_date).exists()
            if overlap_exists:
                errors.setdefault("period_type", "An annual reporting period overlaps with an existing annual period.")

        # 4) Only one ReportingPeriod may have is_baseline_year=True
        if self.is_baseline_year:
            qs_baseline = ReportingPeriod.objects.filter(is_baseline_year=True, is_active=True)
            if self.pk:
                qs_baseline = qs_baseline.exclude(pk=self.pk)
            if qs_baseline.exists():
                errors["is_baseline_year"] = "Only one ReportingPeriod may be marked as the baseline year."

        # 5) CLOSED is terminal: do not allow moving from CLOSED -> OPEN/LOCKED
        if self.pk:
            try:
                previous = ReportingPeriod.objects.get(pk=self.pk)
            except ReportingPeriod.DoesNotExist:
                previous = None
            if previous and previous.status == Status.CLOSED and self.status != Status.CLOSED:
                errors["status"] = "ReportingPeriod in CLOSED state cannot be changed to another status."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ensure model validation is always applied at save time
        self.full_clean()
        # If status became LOCKED and locked_at is not set, set locked_at timestamp (optional helpful behaviour)
        # Keep this idempotent: only set locked_at when status is LOCKED and locked_at not already set.
        # if self.status == Status.LOCKED and not self.locked_at:
        #     self.locked_at = timezone.now()
        super().save(*args, **kwargs)

    def is_editable(self):
        return self.status == Status.OPEN

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
