"""Read-only KPI actual and deterministic target-progress resolution."""
from dataclasses import dataclass
from decimal import Decimal

from apps.data_capture.models import Answer, SubmissionStatus

from ..models import KPIAggregation, KPIDirection, MetricSourceType


@dataclass(frozen=True)
class ActualMetricValue:
    value: Decimal | None
    unit_id: object | None
    source: str
    status: str = "NO_DATA"


def convert_value(value, source_unit_id, target_unit_id):
    """Convert through M4's canonical base-unit factor, or return ``None``."""
    if value is None:
        return None
    if source_unit_id == target_unit_id:
        return Decimal(value)
    if source_unit_id is None or target_unit_id is None:
        return None
    from apps.datapoints.models import Unit
    source = Unit.objects.filter(pk=source_unit_id, is_active=True).first()
    target = Unit.objects.filter(pk=target_unit_id, is_active=True).first()
    if not source or not target or source.family_id != target.family_id:
        return None
    return Decimal(value) * source.factor_to_base / target.factor_to_base


class KPIValueProvider:
    """Provider boundary: approved M5 is first; M6 can register later."""

    @classmethod
    def actual_for(cls, kpi, reporting_period, org_node=None):
        if kpi.metric_source_type != MetricSourceType.DATAPOINT:
            return ActualMetricValue(None, None, "UNSUPPORTED_PROVIDER")
        company_id = kpi.goal.company_id or (org_node.company_id if org_node is not None else None)
        if company_id is None:
            # A historical pre-company Goal must never turn into an
            # unbounded, cross-tenant company-wide aggregate.
            return ActualMetricValue(None, None, "M5_APPROVED", "NO_DATA")
        qs = Answer.objects.filter(
            submission__status=SubmissionStatus.APPROVED,
            submission__data_request__datapoint=kpi.datapoint,
            submission__data_request__reporting_period=reporting_period,
            # Company is needed even for company-wide M10 targets.
            submission__data_request__org_node__company_id=company_id,
        ).select_related("unit", "submission")
        if org_node is not None:
            qs = qs.filter(submission__data_request__org_node=org_node)

        value_field = "integer_value" if kpi.datapoint.data_type == "INTEGER" else "decimal_value"
        answers = [answer for answer in qs if getattr(answer, value_field) is not None]
        if not answers:
            return ActualMetricValue(None, None, "M5_APPROVED", "NO_DATA")
        if kpi.aggregation == KPIAggregation.COUNT:
            return ActualMetricValue(Decimal(len(answers)), None, "M5_APPROVED", "AVAILABLE")
        if kpi.aggregation == KPIAggregation.NONE:
            if len(answers) != 1:
                return ActualMetricValue(None, None, "M5_APPROVED", "AMBIGUOUS")
            answer = answers[0]
            return ActualMetricValue(Decimal(getattr(answer, value_field)), answer.unit_id or kpi.default_unit_id, "M5_APPROVED", "AVAILABLE")

        output_unit_id = kpi.default_unit_id
        normalized = [convert_value(getattr(answer, value_field), answer.unit_id or output_unit_id, output_unit_id) for answer in answers]
        if any(value is None for value in normalized):
            return ActualMetricValue(None, None, "M5_APPROVED_INCOMPATIBLE_UNITS", "NO_DATA")
        if kpi.aggregation == KPIAggregation.SUM:
            return ActualMetricValue(sum(normalized, Decimal("0")), output_unit_id, "M5_APPROVED", "AVAILABLE")
        if kpi.aggregation == KPIAggregation.AVG:
            return ActualMetricValue(sum(normalized, Decimal("0")) / Decimal(len(normalized)), output_unit_id, "M5_APPROVED", "AVAILABLE")
        latest = max(answers, key=lambda answer: (answer.submission.approved_at, str(answer.submission_id), str(answer.id)))
        return ActualMetricValue(Decimal(getattr(latest, value_field)), latest.unit_id or output_unit_id, "M5_APPROVED", "AVAILABLE")


def target_value_in_baseline_unit(target):
    return convert_value(target.target_value, target.target_unit_id, target.baseline_unit_id)


def trajectory_value(target, period):
    """Straight-line annual endpoint interpolation, including endpoints."""
    baseline = target.baseline_period
    endpoint = target.target_period
    if period.start_date < baseline.start_date or period.start_date > endpoint.start_date:
        return None
    span = endpoint.start_date.year - baseline.start_date.year
    if span <= 0:
        return None
    endpoint_value = target_value_in_baseline_unit(target)
    if endpoint_value is None:
        return None
    elapsed = period.start_date.year - baseline.start_date.year
    return target.baseline_value + ((endpoint_value - target.baseline_value) * Decimal(elapsed) / Decimal(span))


def progress_for(target, period):
    expected = trajectory_value(target, period)
    actual = KPIValueProvider.actual_for(target.kpi, period, target.org_node)
    actual_value = convert_value(actual.value, actual.unit_id, target.baseline_unit_id)
    payload = {
        "reporting_period": str(period.id), "trajectory_value": expected,
        "actual_value": actual_value, "actual_unit": str(target.baseline_unit_id) if actual_value is not None and target.baseline_unit_id else None,
        "actual_source": actual.source, "actual_status": actual.status,
        "status": "NO_DATA", "variance": None, "progress_percentage": None,
    }
    if expected is None or actual_value is None:
        return payload
    payload["variance"] = actual_value - expected
    if target.kpi.direction == KPIDirection.REDUCE:
        payload["status"] = "AHEAD" if actual_value < expected else "ON_TRACK" if actual_value == expected else "BEHIND"
    elif target.kpi.direction == KPIDirection.INCREASE:
        payload["status"] = "AHEAD" if actual_value > expected else "ON_TRACK" if actual_value == expected else "BEHIND"
    else:
        payload["status"] = "ON_TRACK" if actual_value == expected else "BEHIND"
    endpoint_value = target_value_in_baseline_unit(target)
    total_change = endpoint_value - target.baseline_value if endpoint_value is not None else None
    if total_change:
        payload["progress_percentage"] = ((actual_value - target.baseline_value) / total_change) * Decimal("100")
    return payload
