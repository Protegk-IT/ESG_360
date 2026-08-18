"""Seed a workflow-ready, repeatable Materiality Assessment demo.

The command deliberately builds on ``seed_demo_foundation`` so a clean local
installation needs only one Materiality seed command.  It creates realistic
example records up to stakeholder setup; it does not pre-complete the survey
or scoring workflow the developer is meant to exercise.
"""

from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.companies.models import Company
from apps.materiality.models import (
    AssessmentTopic,
    InternalScore,
    MaterialSubTopic,
    MaterialTopic,
    MaterialityAssessment,
    Stakeholder,
    StakeholderGroup,
    Survey,
    TopicCategory,
)
from apps.periods.models import ReportingPeriod


class Command(BaseCommand):
    help = (
        "Seed a workflow-ready FY 2025-26 Sahyadri Materiality demo with "
        "topics, stakeholder groups, and named stakeholders."
    )

    # A deliberately distinct name prevents the seed command from attaching
    # demo groups/responses to a real assessment a developer already created
    # for the same financial year.
    assessment_name = "Demo — FY 2025-26 Materiality Assessment"

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

        self.stdout.write(self.style.SUCCESS(
            "Materiality demo seeded: 1 workflow-ready double-materiality assessment, "
            "10 topics, 6 weighted stakeholder groups, and 18 named stakeholders."
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
