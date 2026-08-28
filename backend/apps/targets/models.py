"""Planning records for the M10 Goals, KPI and Targets foundation.

These models deliberately own planning configuration only.  They never copy
captured ESG answers: current values are resolved by a provider from approved
M5 submissions.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import ActivityLogMixin
from apps.core.models import BaseModel


class GoalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class MetricSourceType(models.TextChoices):
    DATAPOINT = "DATAPOINT", "Canonical M4 datapoint"
    CALCULATED_METRIC = "CALCULATED_METRIC", "Calculated metric"
    MANUAL_REFERENCE = "MANUAL_REFERENCE", "Manual/reference metric"


class KPIDirection(models.TextChoices):
    REDUCE = "REDUCE", "Reduce"
    INCREASE = "INCREASE", "Increase"
    MAINTAIN = "MAINTAIN", "Maintain"


class KPIAggregation(models.TextChoices):
    SUM = "SUM", "Sum"
    AVG = "AVG", "Average"
    LATEST = "LATEST", "Latest"
    COUNT = "COUNT", "Count"
    NONE = "NONE", "None"


class TargetType(models.TextChoices):
    ABSOLUTE = "ABSOLUTE", "Absolute"
    INTENSITY = "INTENSITY", "Intensity"
    PERCENTAGE = "PERCENTAGE", "Percentage"


class TargetStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ACHIEVED = "ACHIEVED", "Achieved"
    MISSED = "MISSED", "Missed"
    RETIRED = "RETIRED", "Retired"


class TargetBasis(models.TextChoices):
    PRIOR_YEAR_ACTUAL = "PRIOR_YEAR_ACTUAL", "Prior-year actual"
    PRIOR_REPORT = "PRIOR_REPORT", "Prior report"
    PEER_BENCHMARK = "PEER_BENCHMARK", "Peer benchmark"
    REGULATORY_REQUIREMENT = "REGULATORY_REQUIREMENT", "Regulatory requirement"
    INDUSTRY_STANDARD = "INDUSTRY_STANDARD", "Industry standard"
    SCIENCE_BASED = "SCIENCE_BASED", "Science based"
    CUSTOMER_REQUIREMENT = "CUSTOMER_REQUIREMENT", "Customer requirement"
    MANAGEMENT_COMMITMENT = "MANAGEMENT_COMMITMENT", "Management commitment"
    OTHER = "OTHER", "Other"


class BaselineSource(models.TextChoices):
    SYSTEM_DATA = "SYSTEM_DATA", "Approved system data"
    REFERENCE = "REFERENCE", "Reference/manual"


class InitiativeStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    ONGOING = "ONGOING", "Ongoing"
    COMPLETE = "COMPLETE", "Complete"
    PARKED = "PARKED", "Parked"


class Goal(ActivityLogMixin, BaseModel):
    # Goals are planning records owned by one tenant.  KPIs, targets and
    # initiatives inherit this context through their Goal; they must not
    # attempt to infer it from whichever OrgNode happens to be present.
    # Nullable only for safely migrated legacy goals that predate M10 tenant
    # ownership. New API-created Goals always receive a company; legacy
    # company-wide records intentionally resolve no actual rather than risk a
    # cross-company aggregate.
    company = models.ForeignKey("companies.Company", null=True, blank=True, on_delete=models.PROTECT, related_name="goals")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    material_topic = models.ForeignKey("materiality.MaterialTopic", null=True, blank=True, on_delete=models.SET_NULL, related_name="goals")
    material_subtopic = models.ForeignKey("materiality.MaterialSubTopic", null=True, blank=True, on_delete=models.SET_NULL, related_name="goals")
    source_assessment_topic = models.ForeignKey("materiality.AssessmentTopic", null=True, blank=True, on_delete=models.SET_NULL, related_name="goals")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_goals")
    status = models.CharField(max_length=20, choices=GoalStatus.choices, default=GoalStatus.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_goals")

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["material_topic"]), models.Index(fields=["owner"])]

    def clean(self):
        errors = {}
        if self.material_subtopic_id and self.material_topic_id and self.material_subtopic.topic_id != self.material_topic_id:
            errors["material_subtopic"] = "The material subtopic must belong to the selected material topic."
        if self.source_assessment_topic_id:
            source = self.source_assessment_topic
            if self.material_subtopic_id and source.subtopic_id != self.material_subtopic_id:
                errors["source_assessment_topic"] = "Assessment-topic provenance must match the selected material subtopic."
            if self.material_topic_id and source.subtopic.topic_id != self.material_topic_id:
                errors["source_assessment_topic"] = "Assessment-topic provenance must match the selected material topic."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class KPI(ActivityLogMixin, BaseModel):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="kpis")
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    metric_source_type = models.CharField(max_length=30, choices=MetricSourceType.choices)
    datapoint = models.ForeignKey("datapoints.Datapoint", null=True, blank=True, on_delete=models.PROTECT, related_name="kpis")
    metric_code = models.CharField(max_length=150, blank=True, default="")
    unit_family = models.ForeignKey("datapoints.UnitFamily", null=True, blank=True, on_delete=models.PROTECT, related_name="kpis")
    default_unit = models.ForeignKey("datapoints.Unit", null=True, blank=True, on_delete=models.PROTECT, related_name="kpis")
    direction = models.CharField(max_length=20, choices=KPIDirection.choices)
    aggregation = models.CharField(max_length=20, choices=KPIAggregation.choices, default=KPIAggregation.NONE)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [models.UniqueConstraint(fields=["goal", "code"], name="uq_goal_kpi_code")]

    def clean(self):
        errors = {}
        if self.metric_source_type == MetricSourceType.DATAPOINT:
            if not self.datapoint_id:
                errors["datapoint"] = "A datapoint KPI requires a canonical M4 datapoint."
            elif not self.datapoint.is_active:
                errors["datapoint"] = "Inactive datapoints cannot be used by KPIs."
            elif self.datapoint.data_type not in {"DECIMAL", "INTEGER"}:
                errors["datapoint"] = "Direct M5 actual resolution requires a numeric datapoint."
            elif self.unit_family_id and self.datapoint.unit_family_id != self.unit_family_id:
                errors["unit_family"] = "KPI unit family must match its datapoint."
        elif self.datapoint_id:
            errors["datapoint"] = "Only DATAPOINT KPIs may link directly to an M4 datapoint."
        if self.metric_source_type != MetricSourceType.DATAPOINT and not self.metric_code.strip():
            errors["metric_code"] = "Calculated and manual metrics require a governed metric code."
        if self.default_unit_id:
            if not self.default_unit.is_active:
                errors["default_unit"] = "Inactive units cannot be used by KPIs."
            elif self.unit_family_id and self.default_unit.family_id != self.unit_family_id:
                errors["default_unit"] = "Default unit must belong to the KPI unit family."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.metric_source_type == MetricSourceType.DATAPOINT and self.datapoint_id and not self.unit_family_id:
            self.unit_family = self.datapoint.unit_family
            self.default_unit = self.datapoint.default_unit
        self.full_clean()
        return super().save(*args, **kwargs)


class Target(ActivityLogMixin, BaseModel):
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name="targets")
    org_node = models.ForeignKey("organizations.OrgNode", null=True, blank=True, on_delete=models.PROTECT, related_name="targets")
    baseline_period = models.ForeignKey("periods.ReportingPeriod", on_delete=models.PROTECT, related_name="target_baselines")
    baseline_value = models.DecimalField(max_digits=24, decimal_places=8)
    baseline_unit = models.ForeignKey("datapoints.Unit", null=True, blank=True, on_delete=models.PROTECT, related_name="target_baselines")
    baseline_source = models.CharField(max_length=20, choices=BaselineSource.choices, default=BaselineSource.REFERENCE)
    target_period = models.ForeignKey("periods.ReportingPeriod", on_delete=models.PROTECT, related_name="target_endpoints")
    target_value = models.DecimalField(max_digits=24, decimal_places=8)
    target_unit = models.ForeignKey("datapoints.Unit", null=True, blank=True, on_delete=models.PROTECT, related_name="target_endpoints")
    target_type = models.CharField(max_length=20, choices=TargetType.choices, default=TargetType.ABSOLUTE)
    change_percentage = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_targets")
    status = models.CharField(max_length=20, choices=TargetStatus.choices, default=TargetStatus.DRAFT)
    basis = models.CharField(max_length=30, choices=TargetBasis.choices, default=TargetBasis.OTHER)
    source_reference = models.CharField(max_length=500, blank=True, default="")
    methodology = models.TextField(blank=True, default="")
    rationale = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_targets")

    class Meta:
        ordering = ["-target_period__start_date", "-created_at"]
        indexes = [models.Index(fields=["kpi", "status"]), models.Index(fields=["org_node"])]
        constraints = [
            models.UniqueConstraint(fields=["kpi", "org_node", "target_period"], condition=models.Q(status__in=["DRAFT", "ACTIVE"]), name="uq_active_target_kpi_scope_period"),
            # SQL treats NULL values as distinct in a normal composite unique
            # constraint.  Company-wide targets use org_node=NULL, so they
            # need their own database-level invariant.
            models.UniqueConstraint(fields=["kpi", "target_period"], condition=models.Q(status__in=["DRAFT", "ACTIVE"], org_node__isnull=True), name="uq_active_company_target_kpi_period"),
            # One editable planning window per KPI/scope is intentional for
            # the annual MVP.  It prevents overlapping DRAFT/ACTIVE plans
            # with different endpoints from making progress ambiguous.
            models.UniqueConstraint(fields=["kpi", "org_node"], condition=models.Q(status__in=["DRAFT", "ACTIVE"], org_node__isnull=False), name="uq_editable_target_kpi_org_scope"),
            models.UniqueConstraint(fields=["kpi"], condition=models.Q(status__in=["DRAFT", "ACTIVE"], org_node__isnull=True), name="uq_editable_company_target_kpi"),
        ]

    def clean(self):
        errors = {}
        previous = None
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.status in {
                TargetStatus.ACHIEVED, TargetStatus.MISSED, TargetStatus.RETIRED,
            }:
                immutable = (
                    "kpi_id", "org_node_id", "baseline_period_id", "baseline_value",
                    "baseline_unit_id", "baseline_source", "target_period_id", "target_value",
                    "target_unit_id", "target_type", "change_percentage", "owner_id",
                    "basis", "source_reference", "methodology", "rationale", "status",
                )
                if any(getattr(previous, field) != getattr(self, field) for field in immutable):
                    errors["status"] = "Achieved, missed, and retired targets are immutable historical planning records."
        if self.baseline_period_id and self.target_period_id and self.baseline_period.start_date >= self.target_period.start_date:
            errors["target_period"] = "The target period must start after the baseline period."
        for field in ("baseline_period", "target_period"):
            period = getattr(self, field, None)
            if period and period.period_type != "ANNUAL":
                errors[field] = "M10 target trajectories currently support annual reporting periods only."
        if self.org_node_id and not self.org_node.is_active:
            errors["org_node"] = "Inactive OrgNodes cannot be used by targets."
        if self.org_node_id and self.kpi_id and self.kpi.goal.company_id and self.org_node.company_id != self.kpi.goal.company_id:
            errors["org_node"] = "Target OrgNode must belong to the Goal's company."
        family_id = self.kpi.unit_family_id if self.kpi_id else None
        for field in ("baseline_unit", "target_unit"):
            unit = getattr(self, field)
            if unit and (not unit.is_active or (family_id and unit.family_id != family_id)):
                errors[field] = "Target units must be active and belong to the KPI unit family."
        if (self.baseline_unit_id is None) != (self.target_unit_id is None):
            errors["target_unit"] = "Baseline and target units must either both be set or both be blank."
        target_value_in_baseline_unit = self.target_value
        if (
            self.target_value is not None
            and self.baseline_unit_id
            and self.target_unit_id
            and self.baseline_unit_id != self.target_unit_id
        ):
            target_value_in_baseline_unit = (
                self.target_value * self.target_unit.factor_to_base / self.baseline_unit.factor_to_base
            )
        if self.target_type == TargetType.PERCENTAGE:
            for field, value in (("baseline_value", self.baseline_value), ("target_value", target_value_in_baseline_unit)):
                if value is not None and not Decimal("0") <= value <= Decimal("100"):
                    errors[field] = "Percentage targets must use values between 0 and 100."
        if self.change_percentage is not None and self.baseline_value is not None and target_value_in_baseline_unit is not None:
            if self.baseline_value == Decimal("0"):
                errors["change_percentage"] = "A change percentage cannot be set when the baseline value is zero."
            else:
                expected_change = ((target_value_in_baseline_unit - self.baseline_value) / self.baseline_value * Decimal("100"))
                if abs(expected_change - self.change_percentage) > Decimal("0.0001"):
                    errors["change_percentage"] = "Change percentage must agree with the frozen baseline and target values."
        if self.kpi_id and self.kpi.direction == KPIDirection.MAINTAIN and self.change_percentage not in (None, Decimal("0")):
            errors["change_percentage"] = "Maintain KPIs cannot define a non-zero change percentage."
        if self.kpi_id and self.baseline_value is not None and target_value_in_baseline_unit is not None:
            if self.kpi.direction == KPIDirection.REDUCE and target_value_in_baseline_unit > self.baseline_value:
                errors["target_value"] = "Reduce KPI targets cannot move upward from the baseline."
            elif self.kpi.direction == KPIDirection.INCREASE and target_value_in_baseline_unit < self.baseline_value:
                errors["target_value"] = "Increase KPI targets cannot move downward from the baseline."
            elif self.kpi.direction == KPIDirection.MAINTAIN and target_value_in_baseline_unit != self.baseline_value:
                errors["target_value"] = "Maintain KPI targets must equal the frozen baseline."
        if self.baseline_source == BaselineSource.SYSTEM_DATA and self.kpi_id and self.baseline_period_id:
            # Resolve and compare a real approved source value rather than
            # accepting a user-entered value that is merely labelled system data.
            from .services.progress import KPIValueProvider, convert_value
            actual = KPIValueProvider.actual_for(self.kpi, self.baseline_period, self.org_node)
            if actual.status != "AVAILABLE" or actual.value is None:
                errors["baseline_source"] = "Approved system data is unavailable for this KPI, scope, and baseline period."
            else:
                frozen = convert_value(actual.value, actual.unit_id, self.baseline_unit_id)
                if frozen is None or frozen != self.baseline_value:
                    errors["baseline_value"] = "System-data baselines must equal the resolved approved M5 value."
        if self.status in (TargetStatus.DRAFT, TargetStatus.ACTIVE):
            duplicate = Target.objects.filter(
                kpi_id=self.kpi_id,
                org_node_id=self.org_node_id,
                status__in=(TargetStatus.DRAFT, TargetStatus.ACTIVE),
            )
            if self.pk:
                duplicate = duplicate.exclude(pk=self.pk)
            if duplicate.exists():
                errors["target_period"] = "An editable target already exists for this KPI and scope. Retire it before creating another planning window."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class KPIInitiative(ActivityLogMixin, BaseModel):
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name="initiatives")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    org_node = models.ForeignKey("organizations.OrgNode", null=True, blank=True, on_delete=models.PROTECT, related_name="kpi_initiatives")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_kpi_initiatives")
    status = models.CharField(max_length=20, choices=InitiativeStatus.choices, default=InitiativeStatus.PLANNED)
    due_date = models.DateField(null=True, blank=True)
    anticipated_impact = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["due_date", "name"]

    def clean(self):
        errors = {}
        if self.org_node_id and not self.org_node.is_active:
            errors["org_node"] = "Inactive OrgNodes cannot be used by initiatives."
        if self.org_node_id and self.kpi_id and self.kpi.goal.company_id and self.org_node.company_id != self.kpi.goal.company_id:
            errors["org_node"] = "Initiative OrgNode must belong to the Goal's company."
        if self.anticipated_impact is not None and not Decimal("0") <= self.anticipated_impact <= Decimal("100"):
            errors["anticipated_impact"] = "Anticipated impact must be between 0 and 100."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
