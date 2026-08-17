from django.db.models import Q

from apps.materiality.models import (
    AssessmentTopic,
    InternalScore,
    ScoreRun,
)


# ============================================================
# ASSESSMENT WORKFLOW
# ============================================================

ASSESSMENT_PROGRESS_STEPS = [
    {
        "key": "topics",
        "label": "Manage Topics",
        "percentage": 14,
    },
    {
        "key": "stakeholder_groups",
        "label": "Manage Stakeholder Groups",
        "percentage": 29,
    },
    {
        "key": "stakeholders",
        "label": "Manage Stakeholders",
        "percentage": 43,
    },
    {
        "key": "survey",
        "label": "Manage Survey",
        "percentage": 57,
    },
    {
        "key": "distribution",
        "label": "Survey Distribution",
        "percentage": 71,
    },
    {
        "key": "scoring",
        "label": "Materiality Scoring",
        "percentage": 86,
    },
    {
        "key": "matrix",
        "label": "Materiality Matrix",
        "percentage": 100,
    },
]


# ============================================================
# STEP 1 — TOPICS
# ============================================================

def is_topics_complete(assessment):
    return assessment.assessment_topics.filter(
        is_included=True
    ).exists()


# ============================================================
# STEP 2 — STAKEHOLDER GROUPS
# ============================================================

def is_stakeholder_groups_complete(assessment):
    return assessment.stakeholder_groups.exists()


# ============================================================
# STEP 3 — STAKEHOLDERS
# ============================================================

def is_stakeholders_complete(assessment):
    return assessment.stakeholder_groups.filter(
        stakeholders__isnull=False
    ).exists()


# ============================================================
# STEP 4 — SURVEY
# ============================================================

def is_survey_complete(assessment):
    try:
        survey = assessment.survey
    except Exception:
        return False

    if not survey:
        return False

    return survey.questions.exists()


# ============================================================
# STEP 5 — DISTRIBUTION
# ============================================================

def is_distribution_complete(assessment):
    try:
        survey = assessment.survey
    except Exception:
        return False

    if not survey:
        return False

    return survey.invitations.exists()


# ============================================================
# STEP 6 — SCORING
# ============================================================

def is_scoring_complete(assessment):
    topics = assessment.assessment_topics.filter(
        is_included=True
    )

    topic_count = topics.count()

    if topic_count == 0:
        return False

    # /*
    #  * Internal scoring must exist for every included topic.
    #  */

    internal_score_count = InternalScore.objects.filter(
        assessment_topic__assessment=assessment,
        assessment_topic__is_included=True,
    ).count()

    if internal_score_count < topic_count:
        return False

    # /*
    #  * A ScoreRun means the materiality calculation has
    #  * actually been executed.
    #  */

    return ScoreRun.objects.filter(
        assessment=assessment
    ).exists()


# ============================================================
# STEP 7 — MATRIX
# ============================================================

def is_matrix_complete(assessment):
    latest_score_run = (
        assessment.score_runs
        .order_by("-run_at")
        .first()
    )

    if not latest_score_run:
        return False

    topic_count = assessment.assessment_topics.filter(
        is_included=True
    ).count()

    if topic_count == 0:
        return False

    matrix_topic_count = (
        latest_score_run.topic_results.count()
    )

    return matrix_topic_count >= topic_count


# ============================================================
# ALL STEPS
# ============================================================

def get_assessment_progress_steps(assessment):
    return [
        {
            **ASSESSMENT_PROGRESS_STEPS[0],
            "completed": is_topics_complete(
                assessment
            ),
        },
        {
            **ASSESSMENT_PROGRESS_STEPS[1],
            "completed": is_stakeholder_groups_complete(
                assessment
            ),
        },
        {
            **ASSESSMENT_PROGRESS_STEPS[2],
            "completed": is_stakeholders_complete(
                assessment
            ),
        },
        {
            **ASSESSMENT_PROGRESS_STEPS[3],
            "completed": is_survey_complete(
                assessment
            ),
        },
        {
            **ASSESSMENT_PROGRESS_STEPS[4],
            "completed": is_distribution_complete(
                assessment
            ),
        },
        {
            **ASSESSMENT_PROGRESS_STEPS[5],
            "completed": is_scoring_complete(
                assessment
            ),
        },
        {
            **ASSESSMENT_PROGRESS_STEPS[6],
            "completed": is_matrix_complete(
                assessment
            ),
        },
    ]


# ============================================================
# PROGRESS %
# ============================================================

def get_assessment_progress(assessment):
    steps = get_assessment_progress_steps(
        assessment
    )

    completed_count = sum(
        1
        for step in steps
        if step["completed"]
    )

    return round(
        (
            completed_count
            / len(steps)
        )
        * 100
    )


# ============================================================
# CURRENT STEP
# ============================================================

def get_assessment_current_step(assessment):
    steps = get_assessment_progress_steps(
        assessment
    )

    for step in steps:
        if not step["completed"]:
            return step["label"]

    return "Completed"


def get_assessment_current_step_url(assessment):
    base = f"/materiality/assessments/{assessment.id}"

    steps = get_assessment_progress_steps(assessment)

    step_urls = {
        "Manage Topics": f"{base}/select-topics/",
        "Manage Stakeholder Groups": f"{base}/stakeholders/",
        "Manage Stakeholders": f"{base}/stakeholders/",
        "Manage Survey": f"{base}/survey",
        "Survey Distribution": f"{base}/survey/distribution",
        "Materiality Scoring": f"{base}/scoring",
        "Materiality Matrix": f"{base}/matrix",
        "Completed": f"{base}/results",
    }

    for step in steps:
        if not step["completed"]:
            return step_urls[step["label"]]

    return step_urls["Completed"]


# ============================================================
# COMPLETION
# ============================================================

def is_assessment_completed(assessment):
    return (
        get_assessment_progress(
            assessment
        )
        == 100
    )