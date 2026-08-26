"""Read-only KPI actual and deterministic target-progress resolution."""
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Avg, Sum

from apps.data_capture.models import Answer, SubmissionStatus

from ..models import KPIAggregation, KPIDirection, MetricSourceType


@dataclass(frozen=True)
class ActualMetricValue:
    value: Decimal | None
    unit_id: object | None
    source: str
    status: str = "NO_DATA"


class KPIValueProvider:
    """Provider boundary: M5 is the first provider, M6 can register later."""

    @classmethod
    def actual_for(cls, kpi, reporting_period, org_node=None):
        if kpi.metric_source_type != MetricSourceType.DATAPOINT:
            return ActualMetricValue(None, None, "UNSUPPORTED_PROVIDER")
        qs = Answer.objects.filter(
            submission__status=SubmissionStatus.APPROVED,
            submission__data_request__datapoint=kpi.datapoint,
            submission__data_request__reporting_period=reporting_period,
        )
        if org_node is not None:
            qs = qs.filter(submission__data_request__org_node=org_node)
        # Numeric datapoints are enforced by KPI validation. Unit identity is
        # preserved; conversion is performed only later against the target's
        # explicitly configured unit.
        if kpi.aggregation == KPIAggregation.NONE:
            return ActualMetricValue(None, None, "M5_APPROVED", "NO_DATA")
        if kpi.aggregation == KPIAggregation.COUNT:
            return ActualMetricValue(Decimal(qs.count()), None, "M5_APPROVED", "AVAILABLE")
        units = list(qs.exclude(unit__isnull=True).values_list("unit_id", flat=True).distinct()[:2])
        if len(units) > 1:
            return ActualMetricValue(None, None, "M5_APPROVED_INCOMPATIBLE_UNITS")
        value_field = (
            "integer_value"
            if kpi.datapoint.data_type == "INTEGER"
            else "decimal_value"
        )
        if kpi.aggregation == KPIAggregation.SUM:
            value = qs.aggregate(value=Sum(value_field))["value"]
        elif kpi.aggregation == KPIAggregation.AVG:
            value = qs.aggregate(value=Avg(value_field))["value"]
        else:  # LATEST uses a stable latest approved answer timestamp.
            latest = qs.order_by("-updated_at").first()
            value = getattr(latest, value_field) if latest else None
        return ActualMetricValue(value, units[0] if units else kpi.default_unit_id, "M5_APPROVED", "AVAILABLE" if value is not None else "NO_DATA")


def trajectory_value(target, period):
    """Straight-line endpoint interpolation, including both endpoints."""
    baseline = target.baseline_period
    endpoint = target.target_period
    if period.start_date < baseline.start_date or period.start_date > endpoint.start_date:
        return None
    span = endpoint.start_date.year - baseline.start_date.year
    if span <= 0:
        return None
    elapsed = period.start_date.year - baseline.start_date.year
    target_value = target.target_value
    if target.baseline_unit_id and target.target_unit_id and target.baseline_unit_id != target.target_unit_id:
        target_value = target.target_value * target.target_unit.factor_to_base / target.baseline_unit.factor_to_base
    return target.baseline_value + ((target_value - target.baseline_value) * Decimal(elapsed) / Decimal(span))


def progress_for(target, period):
    expected = trajectory_value(target, period)
    actual = KPIValueProvider.actual_for(target.kpi, period, target.org_node)
    payload = {
        "reporting_period": str(period.id), "trajectory_value": expected,
        "actual_value": actual.value, "actual_unit": str(actual.unit_id) if actual.unit_id else None,
        "actual_source": actual.source, "status": "NO_DATA", "variance": None, "progress_percentage": None,
    }
    if actual.value is not None and actual.unit_id and target.baseline_unit_id and actual.unit_id != target.baseline_unit_id:
        # All metric units have already been constrained to one M4 family.
        from apps.datapoints.models import Unit
        unit = Unit.objects.get(pk=actual.unit_id)
        actual = ActualMetricValue(actual.value * unit.factor_to_base / target.baseline_unit.factor_to_base, target.baseline_unit_id, actual.source, actual.status)
        payload["actual_value"] = actual.value
        payload["actual_unit"] = str(actual.unit_id)
    if expected is None or actual.value is None:
        return payload
    variance = actual.value - expected
    payload["variance"] = variance
    direction = target.kpi.direction
    if direction == KPIDirection.REDUCE:
        payload["status"] = "AHEAD" if actual.value < expected else "ON_TRACK" if actual.value == expected else "BEHIND"
    elif direction == KPIDirection.INCREASE:
        payload["status"] = "AHEAD" if actual.value > expected else "ON_TRACK" if actual.value == expected else "BEHIND"
    else:
        payload["status"] = "ON_TRACK" if actual.value == expected else "BEHIND"
    total_change = target.target_value - target.baseline_value
    if total_change:
        payload["progress_percentage"] = ((actual.value - target.baseline_value) / total_change) * Decimal("100")
    return payload
