"""
apps/materiality/services/scoring.py
 
Pure scoring logic for the materiality assessment module (spec §6).
 
Nothing in this file touches the database directly except read queries —
`run_scoring()` is the only function that writes, and it delegates all the
actual math to the pure functions below so they can be unit-tested against
a hand-calculated example without spinning up fixtures for a full survey.
 
Method version: bump METHOD_VERSION any time the formulas below change.
It gets frozen into every ScoreRun snapshot (§6.6) so old runs stay
reproducible even after the algorithm evolves.
"""
 
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
 
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
 
METHOD_VERSION = "1.0"
 
TWO_PLACES = Decimal("0.01")
 
 
def _round2(value) -> Decimal:
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
 
 
# ---------------------------------------------------------------------------
# §6.1 — Weighted stakeholder aggregation
# ---------------------------------------------------------------------------
 
@dataclass
class GroupResponses:
    group_id: str
    weight: Decimal
    values: list  # raw integer response values from that group's members
 
 
def weighted_aggregate(group_responses: list[GroupResponses]) -> Optional[Decimal]:
    """
    primary_score = Σ(weight_g × avg_g) / Σ(weight_g)   — over groups that
    actually responded. Groups with zero responses are dropped from BOTH
    the numerator and denominator, so a silent non-responding group never
    drags the score down (spec §6.1).
 
    Returns None if no group has any responses at all — caller decides
    what to do with a topic that has no data.
    """
    responding = [g for g in group_responses if g.values]
    if not responding:
        return None
 
    weight_sum = sum(g.weight for g in responding)
    if weight_sum == 0:
        # All responding groups happen to have zero weight — avoid
        # dividing by zero; treat as no usable data.
        return None
 
    numerator = sum(
        g.weight * (sum(g.values) / Decimal(len(g.values)))
        for g in responding
    )
    return _round2(numerator / weight_sum)
 
 
def validate_group_weights(weights: list[Decimal], tolerance: Decimal = Decimal("0.01")) -> None:
    """
    §3.2: stakeholder group weights across one assessment must sum to 100.
    Reject the score run if they don't (acceptance criteria #3).
    """
    total = sum(weights) if weights else Decimal("0")
    if abs(total - Decimal("100")) > tolerance:
        raise ValidationError(
            f"Stakeholder group weights must total 100 (currently {total})."
        )
 
 
# ---------------------------------------------------------------------------
# §6.2 — Internal expert scoring (double mode only)
# ---------------------------------------------------------------------------
 
def compute_internal_impact(scale: int, scope: int, irremediability: int,
                             impact_type: str, likelihood: Optional[int]) -> Decimal:
    severity = (Decimal(scale) + Decimal(scope) + Decimal(irremediability)) / Decimal(3)
 
    if impact_type == "ACTUAL":
        return _round2(severity)
 
    # POTENTIAL — likelihood is required per the model, but guard anyway.
    if likelihood is None:
        raise ValidationError("likelihood is required for a POTENTIAL impact_type.")
    return _round2(severity * (Decimal(likelihood) / Decimal(5)))
 
 
def compute_internal_financial(financial_magnitude: int, financial_likelihood: int) -> Decimal:
    return _round2(
        (Decimal(financial_magnitude) * Decimal(financial_likelihood)) / Decimal(5)
    )
 
 
# ---------------------------------------------------------------------------
# §6.3 — Blending survey + internal scores
# ---------------------------------------------------------------------------
 
def blend_scores(mode: str, blend_weight: Decimal,
                  survey_primary: Optional[Decimal], survey_secondary: Optional[Decimal],
                  internal_impact: Optional[Decimal], internal_financial: Optional[Decimal]
                  ) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Returns (final_primary, final_secondary).
 
    SINGLE mode, or double mode with no internal score recorded yet:
    the survey score passes through unchanged (§6.3). Internal-only
    inputs (no survey data) are also handled — blend_weight still
    applies, the missing side just contributes nothing.
    """
    if mode == "SINGLE" or internal_impact is None:
        return survey_primary, survey_secondary
 
    w = blend_weight
 
    def blend(survey_val, internal_val):
        if survey_val is None and internal_val is None:
            return None
        if survey_val is None:
            return _round2(internal_val)
        if internal_val is None:
            return _round2(survey_val)
        return _round2((Decimal(1) - w) * survey_val + w * internal_val)
 
    return blend(survey_primary, internal_impact), blend(survey_secondary, internal_financial)
 
 
# ---------------------------------------------------------------------------
# §6.4 — Classification
# ---------------------------------------------------------------------------
 
def classify(mode: str, primary: Optional[Decimal], secondary: Optional[Decimal],
             primary_threshold: Decimal, secondary_threshold: Decimal) -> str:
    if primary is None or secondary is None:
        return "INSUFFICIENT_DATA"
 
    primary_hit = primary >= primary_threshold
    secondary_hit = secondary >= secondary_threshold
 
    if mode == "SINGLE":
        if primary_hit and secondary_hit:
            return "MATERIAL"
        if primary_hit or secondary_hit:
            return "MONITOR"
        return "NOT_MATERIAL"
 
    # DOUBLE
    if primary_hit and secondary_hit:
        return "DOUBLE_MATERIAL"
    if primary_hit:
        return "IMPACT_MATERIAL"
    if secondary_hit:
        return "FINANCIAL_MATERIAL"
    return "NOT_MATERIAL"
 
 
# ---------------------------------------------------------------------------
# Orchestration — this is the only part that touches the DB.
# ---------------------------------------------------------------------------
 
@dataclass
class TopicScoreResult:
    assessment_topic_id: str
    primary_score: Optional[Decimal]
    secondary_score: Optional[Decimal]
    classification: str
    is_override: bool = False
 
 
def _survey_dimension_scores(assessment, assessment_topic, dimension):
    """
    Pulls raw SurveyResponse values for one (assessment_topic, dimension)
    pair, grouped by stakeholder group, and returns a list[GroupResponses]
    ready for weighted_aggregate().
    """
    # Local imports to keep this module import-order-safe (services
    # importing models is normal in Django, but avoids a circular import
    # at module load time if models ever import this file for constants).
    from apps.materiality.models import StakeholderGroup, SurveyResponse
 
    groups = StakeholderGroup.objects.filter(assessment=assessment)
 
    responses = (
        SurveyResponse.objects
        .filter(
            question__assessment_topic=assessment_topic,
            question__dimension=dimension,
            question__survey__assessment=assessment,
            value__isnull=False,
        )
        .select_related("invitation__stakeholder__group")
    )
 
    values_by_group: dict = {}
    for r in responses:
        gid = r.invitation.stakeholder.group_id
        values_by_group.setdefault(gid, []).append(r.value)
 
    return [
        GroupResponses(
            group_id=str(g.id),
            weight=g.weight,
            values=values_by_group.get(g.id, []),
        )
        for g in groups
    ]
 
 
def _dimensions_for_mode(mode: str) -> tuple[str, str]:
    """Returns (primary_dimension, secondary_dimension) for the survey."""
    if mode == "SINGLE":
        return "IMPACT", "STAKEHOLDER_IMPORTANCE"
    return "IMPACT", "FINANCIAL"
 
 
def score_assessment_topic(assessment, assessment_topic) -> TopicScoreResult:
    """Computes the final scores + classification for one AssessmentTopic."""
    primary_dim, secondary_dim = _dimensions_for_mode(assessment.mode)
 
    survey_primary = weighted_aggregate(
        _survey_dimension_scores(assessment, assessment_topic, primary_dim)
    )
    survey_secondary = weighted_aggregate(
        _survey_dimension_scores(assessment, assessment_topic, secondary_dim)
    )
 
    internal_impact = internal_financial = None
    if assessment.mode == "DOUBLE" and hasattr(assessment_topic, "internal_score"):
        score = assessment_topic.internal_score
        internal_impact = compute_internal_impact(
            score.scale, score.scope, score.irremediability,
            score.impact_type, score.likelihood,
        )
        internal_financial = compute_internal_financial(
            score.financial_magnitude, score.financial_likelihood,
        )
 
    final_primary, final_secondary = blend_scores(
        assessment.mode, assessment.internal_blend_weight,
        survey_primary, survey_secondary,
        internal_impact, internal_financial,
    )
 
    computed_classification = classify(
        assessment.mode, final_primary, final_secondary,
        assessment.primary_threshold, assessment.secondary_threshold,
    )
 
    # §6.5 — an override survives re-scoring: raw scores refresh, the
    # stored classification does not.
    if assessment_topic.is_override:
        final_classification = assessment_topic.classification
    else:
        final_classification = computed_classification
 
    return TopicScoreResult(
        assessment_topic_id=str(assessment_topic.id),
        primary_score=final_primary,
        secondary_score=final_secondary,
        classification=final_classification,
        is_override=assessment_topic.is_override,
    )
 
 
@transaction.atomic
def run_scoring(assessment, user):
    """
    Executes a full score run for an assessment (§6.6):
      1. validates stakeholder weights sum to 100
      2. scores every included AssessmentTopic
      3. writes the raw scores + classification back onto AssessmentTopic
      4. snapshots the whole thing into ScoreRun + ScoreRunTopic
 
    Returns the created ScoreRun instance.
    """
    from apps.materiality.models import (
        AssessmentTopic, ScoreRun, ScoreRunTopic, StakeholderGroup,
        SurveyInvitation,
    )
 
    if assessment.is_locked:
        raise ValidationError("This assessment is approved and locked; it cannot be re-scored.")
 
    groups = list(StakeholderGroup.objects.filter(assessment=assessment))
    validate_group_weights([g.weight for g in groups])
 
    topics = list(
        AssessmentTopic.objects
        .filter(assessment=assessment, is_included=True)
        .select_related("subtopic")
    )
    if not topics:
        raise ValidationError("Cannot run scoring: no included topics on this assessment.")
 
    results = [score_assessment_topic(assessment, t) for t in topics]
 
    invited_count = SurveyInvitation.objects.filter(survey__assessment=assessment).count()
    response_count = SurveyInvitation.objects.filter(
        survey__assessment=assessment, submitted_at__isnull=False,
    ).count()
 
    score_run = ScoreRun.objects.create(
        assessment=assessment,
        mode=assessment.mode,
        thresholds_snapshot={
            "primary_threshold": str(assessment.primary_threshold),
            "secondary_threshold": str(assessment.secondary_threshold),
            "internal_blend_weight": str(assessment.internal_blend_weight),
        },
        group_weights_snapshot={
            str(g.id): {"name": g.name, "weight": str(g.weight)} for g in groups
        },
        response_count=response_count,
        invited_count=invited_count,
        method_version=METHOD_VERSION,
        run_by=user,
    )
 
    topic_by_id = {str(t.id): t for t in topics}
    score_run_topics = []
    for result in results:
        topic = topic_by_id[result.assessment_topic_id]
 
        # Persist raw scores; classification only if not manually overridden.
        topic.primary_score = result.primary_score
        topic.secondary_score = result.secondary_score
        if not topic.is_override:
            topic.classification = result.classification
        topic.save(update_fields=["primary_score", "secondary_score", "classification"])
 
        score_run_topics.append(ScoreRunTopic(
            score_run=score_run,
            assessment_topic=topic,
            primary_score=result.primary_score if result.primary_score is not None else Decimal("0.00"),
            secondary_score=result.secondary_score if result.secondary_score is not None else Decimal("0.00"),
            classification=result.classification,
        ))
 
    ScoreRunTopic.objects.bulk_create(score_run_topics)
 
    if assessment.status != "APPROVED":
        assessment.status = "SCORED"
        assessment.save(update_fields=["status"])
 
    return score_run