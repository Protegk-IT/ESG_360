"""
apps/materiality/services/pdf_export.py

Builds the "Export" screen's PDF summary (§9 screen 11, Phase 7).
Pure generation logic — takes an assessment, returns PDF bytes. No
request/response handling here; that's the view's job.

Requires reportlab:
    pip install reportlab --break-system-packages
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_summary_pdf(assessment) -> bytes:
    """
    Renders a one-shot PDF summary of an assessment: header info,
    latest score run stats, and a scored sub-topic table. Returns
    raw PDF bytes ready to hand to an HttpResponse.
    """
    from apps.materiality.models import AssessmentTopic, ScoreRun

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"{assessment.name} - Materiality Summary",
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # =========================================================
    # HEADER
    # =========================================================

    elements.append(Paragraph(assessment.name, styles["Title"]))

    company_name = (
        assessment.company.company_name if assessment.company else "-"
    )

    elements.append(
        Paragraph(f"Company: {company_name}", styles["Normal"])
    )

    elements.append(
        Paragraph(
            f"Mode: {assessment.get_mode_display()}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"Status: {assessment.get_status_display()}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"Thresholds: primary {assessment.primary_threshold}, "
            f"secondary {assessment.secondary_threshold}",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 12))

    # =========================================================
    # LATEST SCORE RUN
    # =========================================================

    latest_run = (
        ScoreRun.objects
        .filter(assessment=assessment)
        .order_by("-run_at")
        .first()
    )

    if latest_run:
        elements.append(
            Paragraph(
                f"Latest score run: {latest_run.run_at.strftime('%d %b %Y, %H:%M')} "
                f"&mdash; {latest_run.response_count} of "
                f"{latest_run.invited_count} stakeholders responded "
                f"(method {latest_run.method_version})",
                styles["Normal"],
            )
        )
    else:
        elements.append(
            Paragraph(
                "No score run has been executed for this assessment yet.",
                styles["Normal"],
            )
        )

    elements.append(Spacer(1, 16))

    # =========================================================
    # SCORE TABLE
    # =========================================================

    assessment_topics = (
        AssessmentTopic.objects
        .filter(
            assessment=assessment,
            is_included=True,
        )
        .select_related(
            "subtopic",
            "subtopic__topic",
            "subtopic__topic__category",
        )
        .order_by("display_order")
    )

    table_data = [[
        "Category",
        "Sub-topic",
        "Primary",
        "Secondary",
        "Classification",
        "Override",
    ]]

    for assessment_topic in assessment_topics:
        subtopic = assessment_topic.subtopic

        table_data.append([
            subtopic.topic.category.name,
            subtopic.name,
            (
                str(assessment_topic.primary_score)
                if assessment_topic.primary_score is not None
                else "-"
            ),
            (
                str(assessment_topic.secondary_score)
                if assessment_topic.secondary_score is not None
                else "-"
            ),
            assessment_topic.classification or "NOT_SCORED",
            "Yes" if assessment_topic.is_override else "No",
        ])

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))

    elements.append(table)

    doc.build(elements)

    return buffer.getvalue()