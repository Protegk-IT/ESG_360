"""Seed deterministic Materiality Assessment UI/demo states.

The command deliberately builds on ``seed_demo_foundation`` so a clean local
installation needs only one Materiality seed command.  It creates realistic
three explicitly named assessments: a blank draft, a workflow-ready assessment
for manual survey testing, and a completed historical record for results UI.
"""

from datetime import date
from decimal import Decimal
from django.utils import timezone

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.companies.models import Company
from apps.materiality.models import (
    AssessmentTopic,
    InternalScore,
    ScaleDefinition,
    MaterialSubTopic,
    MaterialTopic,
    MaterialityAssessment,
    Stakeholder,
    StakeholderGroup,
    Survey,
    SurveyInvitation,
    SurveyGroupLink,
    SurveyQuestion,
    SurveyResponse,
    SurveySubmission,
    TopicCategory,
)
from apps.materiality.services.scoring import run_scoring
from apps.periods.models import ReportingPeriod


class Command(BaseCommand):
    help = (
        "Reset the three named FY 2025-26 Sahyadri Materiality UI demos: "
        "Draft, Workflow-ready, and Completed. User-created assessments are untouched."
    )

    # A deliberately distinct name prevents the seed command from attaching
    # demo groups/responses to a real assessment a developer already created
    # for the same financial year.
    assessment_name = "Demo — FY 2025-26 Materiality Assessment"
    draft_assessment_name = "Demo — Draft Materiality Assessment"
    completed_assessment_name = "Demo — Completed Materiality Assessment"

    # (category, topic/subtopic name)
    TOPICS = (
        ("E", "Climate change and emissions"),
        ("S", "Occupational health and safety"),
        ("G", "Business ethics and anti-bribery"),
        ("E", "Water and effluents"),
        ("E", "Waste and circularity"),
        ("S", "Labour practices"),
        ("G", "Data privacy"),
        ("E", "Air quality"),
        ("S", "Diversity and inclusion"),
        ("S", "Community relations"),
    )

    GROUPS = (
        ("Investors", "Investors and lenders", Decimal("25.00")),
        ("Employees", "Employees and worker representatives", Decimal("20.00")),
        ("Customers", "Customers and end users", Decimal("20.00")),
        ("Suppliers", "Suppliers and business partners", Decimal("15.00")),
        ("Communities", "Communities near operating sites", Decimal("10.00")),
        ("Regulators", "Regulators and public authorities", Decimal("10.00")),
    )

    STAKEHOLDERS = {
        "Investors": (
            ("Aarav Shah", "aarav.shah@northstar-capital.example", "Northstar Capital", "ESG Analyst"),
            ("Kavya Iyer", "kavya.iyer@evergreen-funds.example", "Evergreen Funds", "Portfolio Manager"),
            ("Rohan Mehta", "rohan.mehta@lender.example", "Sahyadri Lending Bank", "Credit Risk Manager"),
        ),
        "Employees": (
            ("Priya Nair", "priya.nair@employees.example", "Sahyadri Auto Components", "Plant Supervisor"),
            ("Vikram Rao", "vikram.rao@employees.example", "Sahyadri Auto Components", "EHS Officer"),
            ("Neha Kapoor", "neha.kapoor@employees.example", "Sahyadri Auto Components", "HR Business Partner"),
        ),
        "Customers": (
            ("Anika Bose", "anika.bose@customers.example", "Mobility Systems India", "Supplier Development Lead"),
            ("Dev Malhotra", "dev.malhotra@customers.example", "Precision Mobility", "Procurement Manager"),
            ("Sana Khan", "sana.khan@customers.example", "EV Components Co.", "Quality Manager"),
        ),
        "Suppliers": (
            ("Harish Patel", "harish.patel@suppliers.example", "SteelWorks India", "Key Account Manager"),
            ("Isha Verma", "isha.verma@suppliers.example", "GreenPack Solutions", "Sustainability Lead"),
            ("Manoj Das", "manoj.das@suppliers.example", "Logistics Partners", "Operations Director"),
        ),
        "Communities": (
            ("Sunita Jadhav", "sunita.jadhav@community.example", "Chakan Community Forum", "Community Representative"),
            ("Amit Kulkarni", "amit.kulkarni@community.example", "Pune Environment Network", "Programme Coordinator"),
            ("Leela Thomas", "leela.thomas@community.example", "Hosur Development Trust", "Trustee"),
        ),
        "Regulators": (
            ("Nitin Deshmukh", "nitin.deshmukh@regulators.example", "State Pollution Control Board", "Environmental Officer"),
            ("Farah Siddiqui", "farah.siddiqui@regulators.example", "Labour Department", "Labour Inspector"),
            ("Suresh Babu", "suresh.babu@regulators.example", "Industrial Safety Directorate", "Safety Officer"),
        ),
    }

    # (impact/primary, financial/secondary) targets for the completed demo.
    # They deliberately exercise every matrix quadrant while keeping the
    # seed repeatable and easy for a developer to reason about.
    COMPLETED_SCORE_PROFILES = (
        (5, 5), (4, 2), (2, 4), (2, 2), (4, 4),
        (3, 5), (5, 3), (1, 3), (3, 3), (4, 5),
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner",
            help="Username recorded as the assessment creator, scorer, and override author. "
            "Defaults to the first superuser, then the first active user.",
        )

    def handle(self, *args, **options):
        # This is intentionally a complete demo command for a clean checkout.
        call_command("seed_demo_foundation", verbosity=0)
        owner = self._owner(options.get("owner"))

        with transaction.atomic():
            company = Company.objects.get(company_code="SAHY")
            period = ReportingPeriod.objects.get(
                parent__isnull=True,
                period_type="ANNUAL",
                start_date=date(2025, 4, 1),
                end_date=date(2026, 3, 31),
            )
            assessment, _ = MaterialityAssessment.objects.get_or_create(
                company=company,
                reporting_period=period,
                name=self.assessment_name,
                defaults={
                    "mode": "DOUBLE",
                    "status": "IN_PROGRESS",
                    "primary_threshold": Decimal("3.50"),
                    "secondary_threshold": Decimal("3.50"),
                    "scale_min": 1,
                    "scale_max": 5,
                    "internal_blend_weight": Decimal("0.50"),
                    "created_by": owner,
                },
            )
            self._ensure_assessment_configuration(assessment, owner)
            self._ensure_topics(assessment)
            groups = self._ensure_groups(assessment)
            self._ensure_stakeholders(groups)
            self._reset_workflow_state(assessment)
            self._ensure_workflow_ready_survey(assessment, groups)
            self._ensure_draft(company, period, owner)
            self._ensure_completed(company, period, owner)

        self.stdout.write(self.style.SUCCESS(
            "Materiality demo seeded: draft, workflow-ready, and completed/locked assessments."
        ))

    def _owner(self, username):
        if username:
            try:
                return User.objects.get(username=username, is_active=True)
            except User.DoesNotExist as exc:
                raise CommandError(f"Active user {username!r} does not exist.") from exc
        return (
            User.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
            or User.objects.filter(is_active=True).order_by("id").first()
            or self._no_owner()
        )

    @staticmethod
    def _no_owner():
        raise CommandError(
            "Create a user first (for example with createsuperuser), or pass --owner <username>."
        )

    @staticmethod
    def _ensure_assessment_configuration(assessment, owner):
        assessment.mode = "DOUBLE"
        assessment.status = "IN_PROGRESS"
        assessment.primary_threshold = Decimal("3.50")
        assessment.secondary_threshold = Decimal("3.50")
        assessment.scale_min = 1
        assessment.scale_max = 5
        assessment.internal_blend_weight = Decimal("0.50")
        assessment.is_locked = False
        assessment.approved_by = None
        assessment.approved_at = None
        if assessment.created_by_id is None:
            assessment.created_by = owner
        assessment.save()

    def _ensure_topics(self, assessment):
        categories = {category.code: category for category in TopicCategory.objects.all()}
        result = {}
        for order, (category_code, name) in enumerate(self.TOPICS, start=1):
            category = categories[category_code]
            topic, _ = MaterialTopic.objects.get_or_create(
                category=category,
                company=None,
                name=name,
                defaults={
                    "description": f"Demo Materiality topic: {name}.",
                    "display_order": 100 + order,
                    "is_active": True,
                },
            )
            subtopic, _ = MaterialSubTopic.objects.get_or_create(
                topic=topic,
                name=name,
                defaults={
                    "description": f"Assessment scoring scope for {name}.",
                    "display_order": 1,
                    "is_active": True,
                },
            )
            assessment_topic, _ = AssessmentTopic.objects.get_or_create(
                assessment=assessment,
                subtopic=subtopic,
                defaults={"is_included": True, "display_order": order},
            )
            result[name] = assessment_topic
        return result

    def _ensure_groups(self, assessment):
        result = {}
        for name, description, weight in self.GROUPS:
            group, _ = StakeholderGroup.objects.update_or_create(
                assessment=assessment,
                name=name,
                defaults={"description": description, "weight": weight, "is_internal": False},
            )
            result[name] = group
        unexpected = assessment.stakeholder_groups.exclude(name__in=result).values_list("name", flat=True)
        if unexpected:
            raise CommandError(
                "The demo assessment contains non-demo stakeholder groups: "
                f"{', '.join(unexpected)}. Remove them from the demo assessment before reseeding."
            )
        return result

    def _ensure_stakeholders(self, groups):
        for group_name, records in self.STAKEHOLDERS.items():
            group = groups[group_name]
            for name, email, organisation, designation in records:
                Stakeholder.objects.update_or_create(
                    group=group,
                    email=email,
                    defaults={
                        "name": name,
                        "organisation": organisation,
                        "designation": designation,
                    },
                )

    @staticmethod
    def _reset_workflow_state(assessment):
        """Reset only the explicitly named demo assessment to its setup stage."""
        Survey.objects.filter(assessment=assessment).delete()
        assessment.score_runs.all().delete()
        InternalScore.objects.filter(assessment_topic__assessment=assessment).delete()
        assessment.assessment_topics.update(
            primary_score=None,
            secondary_score=None,
            classification="",
            is_override=False,
            override_reason="",
            override_by=None,
        )

    def _ensure_draft(self, company, period, owner):
        draft, _ = MaterialityAssessment.objects.update_or_create(
            company=company, reporting_period=period, name=self.draft_assessment_name,
            defaults={"mode": "DOUBLE", "status": "DRAFT", "primary_threshold": Decimal("3.50"),
                      "secondary_threshold": Decimal("3.50"), "scale_min": 1, "scale_max": 5,
                      "internal_blend_weight": Decimal("0.50"), "created_by": owner,
                      "is_locked": False, "approved_by": None, "approved_at": None},
        )
        Survey.objects.filter(assessment=draft).delete()
        draft.score_runs.all().delete()
        draft.assessment_topics.all().delete()

    @staticmethod
    def _survey_questions(assessment, survey):
        """Create the same two dimensions the DOUBLE-mode generator uses."""
        scales = {
            scale.dimension: scale
            for scale in ScaleDefinition.objects.filter(assessment__isnull=True)
        }
        questions = []
        for order, topic in enumerate(
            assessment.assessment_topics.select_related("subtopic").order_by("display_order"),
            start=1,
        ):
            questions.extend([
                SurveyQuestion(
                    survey=survey, assessment_topic=topic, scale=scales["IMPACT"],
                    dimension="IMPACT", question_text=f"Impact: {topic.subtopic.name}",
                    display_order=order * 2 - 1,
                ),
                SurveyQuestion(
                    survey=survey, assessment_topic=topic, scale=scales["FINANCIAL"],
                    dimension="FINANCIAL", question_text=f"Financial: {topic.subtopic.name}",
                    display_order=order * 2,
                ),
            ])
        SurveyQuestion.objects.bulk_create(questions)

    def _ensure_workflow_ready_survey(self, assessment, groups):
        """Create real READY survey, invitation, and group-link records for UI testing."""
        survey = Survey.objects.create(
            assessment=assessment,
            title="Workflow-ready Materiality Survey",
            status="READY",
        )
        self._survey_questions(assessment, survey)
        SurveyGroupLink.objects.bulk_create([
            SurveyGroupLink(survey=survey, stakeholder_group=group)
            for group in groups.values()
        ])
        SurveyInvitation.objects.bulk_create([
            SurveyInvitation(survey=survey, stakeholder=stakeholder, status="NOT_SENT")
            for group in groups.values()
            for stakeholder in group.stakeholders.all()
        ])

    def _ensure_completed(self, company, period, owner):
        assessment, _ = MaterialityAssessment.objects.update_or_create(
            company=company, reporting_period=period, name=self.completed_assessment_name,
            defaults={"mode": "DOUBLE", "status": "IN_PROGRESS", "primary_threshold": Decimal("3.50"),
                      "secondary_threshold": Decimal("3.50"), "scale_min": 1, "scale_max": 5,
                      "internal_blend_weight": Decimal("0.50"), "created_by": owner,
                      "is_locked": False, "approved_by": None, "approved_at": None},
        )
        self._ensure_assessment_configuration(assessment, owner)
        topics = self._ensure_topics(assessment)
        groups = self._ensure_groups(assessment)
        self._ensure_stakeholders(groups)
        Survey.objects.filter(assessment=assessment).delete()
        assessment.score_runs.all().delete()
        InternalScore.objects.filter(assessment_topic__assessment=assessment).delete()
        survey = Survey.objects.create(assessment=assessment, title="Completed Materiality Survey", status="CLOSED")
        self._survey_questions(assessment, survey)
        questions = list(survey.questions.all())
        for group_index, group in enumerate(groups.values()):
            SurveyGroupLink.objects.create(survey=survey, stakeholder_group=group)
            for respondent_index in range(3):
                # One tracked invitation and multiple independent anonymous
                # submissions demonstrate both distribution methods while
                # giving each group enough data for a useful matrix fixture.
                invitation = None
                if group_index == 0 and respondent_index == 0:
                    invitation = SurveyInvitation.objects.create(
                        survey=survey,
                        stakeholder=group.stakeholders.order_by("id").first(),
                        status="SUBMITTED",
                        submitted_at=timezone.now(),
                    )
                submission = SurveySubmission.objects.create(
                    survey=survey,
                    stakeholder_group=group,
                    invitation=invitation,
                    source="IDENTIFIED" if invitation else "ANONYMOUS",
                    submitted_at=timezone.now(),
                )
                SurveyResponse.objects.bulk_create([
                    SurveyResponse(
                        submission=submission,
                        question=question,
                        # Three independent submissions per group provide a
                        # small response distribution whose average is the
                        # profile target. The matrix therefore remains
                        # scattered while the result is deterministic.
                        value=max(
                            1,
                            min(
                                5,
                                self.COMPLETED_SCORE_PROFILES[(question.display_order - 1) // 2][
                                    1 if question.dimension == "FINANCIAL" else 0
                                ] + respondent_index - 1,
                            ),
                        ),
                        answered_at=timezone.now(),
                    )
                    for question in questions
                ])
        InternalScore.objects.bulk_create([
            InternalScore(
                assessment_topic=topic,
                impact_type="ACTUAL",
                scale=self.COMPLETED_SCORE_PROFILES[index][0],
                scope=self.COMPLETED_SCORE_PROFILES[index][0],
                irremediability=self.COMPLETED_SCORE_PROFILES[index][0],
                financial_magnitude=self.COMPLETED_SCORE_PROFILES[index][1],
                financial_likelihood=5,
                rationale="Deterministic completed demo score.",
                scored_by=owner,
            )
            for index, topic in enumerate(assessment.assessment_topics.order_by("display_order"))
        ])
        first_topic = assessment.assessment_topics.order_by("display_order").first()
        first_topic.is_override, first_topic.override_reason, first_topic.override_by = True, "Seeded example of a documented management override.", owner
        first_topic.classification = "DOUBLE_MATERIAL"
        first_topic.save(update_fields=["is_override", "override_reason", "override_by", "classification"])
        run_scoring(assessment, owner)
        assessment.status, assessment.is_locked, assessment.approved_by, assessment.approved_at = "COMPLETED", True, owner, timezone.now()
        assessment.save(update_fields=["status", "is_locked", "approved_by", "approved_at"])
