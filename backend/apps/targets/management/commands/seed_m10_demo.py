"""Seed a small, repeatable M10 planning demo without resetting a database."""

from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.data_capture.models import DataRequest, SubmissionStatus
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    Unit,
    UnitFamily,
)
from apps.materiality.models import MaterialTopic
from apps.modules.models import Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod, Status as PeriodStatus
from apps.targets.models import (
    BaselineSource,
    Goal,
    GoalStatus,
    KPI,
    KPIAggregation,
    KPIDirection,
    MetricSourceType,
    Target,
    TargetBasis,
    TargetStatus,
    TargetType,
)


class Command(BaseCommand):
    help = (
        "Seed a controlled M10 demo: Goals/KPIs/Targets plus real approved M5 "
        "answers. Re-running is safe and does not reset existing data."
    )

    def handle(self, *args, **options):
        # These established seeds own their own reference records and are
        # idempotent. They make this demo usable on a fresh local database.
        for command in ("seed_modules", "seed_rbac", "seed_datapoints", "seed_materiality", "seed_demo_foundation"):
            call_command(command, verbosity=0)

        with transaction.atomic():
            company = Company.objects.filter(is_active=True).order_by("company_code").first()
            if not company:
                raise CommandError("No active company is available for the M10 demo.")
            org_node = self._demo_org_node(company)
            maker, reviewer = self._demo_users(org_node)
            periods = self._demo_periods()
            datapoints = self._datapoints()
            self._seed_approved_values(datapoints, periods["actual"], org_node, maker, reviewer)
            self._seed_goals(company, datapoints, periods, org_node, reviewer)

        self.stdout.write(self.style.SUCCESS(
            "M10 demo seeded: 4 DEMO M10 goals, real approved M5 values across "
            "three historical periods, and future target trajectories."
        ))

    def _demo_org_node(self, company):
        root = OrgNode.objects.filter(company=company, parent__isnull=True).first()
        if not root:
            raise CommandError("The active company has no root OrgNode.")
        node, created = OrgNode.objects.get_or_create(
            company=company,
            code="DEMO_M10_PLANT_PUNE",
            defaults={
                "name": "DEMO M10 Plant — Pune",
                "node_type": "FACILITY",
                "parent": root,
                "facility_type": "Demo planning facility",
                "operational_control": True,
            },
        )
        if not created and (node.parent_id != root.id or not node.is_active):
            node.parent = root
            node.is_active = True
            node.save()
        return node

    def _demo_users(self, org_node):
        maker, _ = User.objects.get_or_create(
            username="DEMO_M10_MAKER",
            defaults={"email": "demo.m10.maker@example.invalid", "is_active": True},
        )
        reviewer, _ = User.objects.get_or_create(
            username="DEMO_M10_REVIEWER",
            defaults={"email": "demo.m10.reviewer@example.invalid", "is_active": True},
        )
        for user in (maker, reviewer):
            user.is_active = True
            user.set_unusable_password()
            user.save(update_fields=["is_active", "password"])

        data_entry = Role.objects.get(role_code="data_entry")
        reviewer_role = Role.objects.get(role_code="reviewer")
        UserRoleAssignment.objects.get_or_create(
            user=maker, role=data_entry, org_node=org_node, module_code="data"
        )
        UserRoleAssignment.objects.get_or_create(
            user=reviewer, role=reviewer_role, org_node=org_node, module_code="data"
        )
        return maker, reviewer

    @staticmethod
    def _annual_is_free(start_year):
        start = date(start_year, 4, 1)
        end = date(start_year + 1, 3, 31)
        return not ReportingPeriod.objects.filter(
            period_type=PeriodType.ANNUAL,
            is_active=True,
            start_date__lte=end,
            end_date__gte=start,
        ).exists()

    def _demo_periods(self):
        existing = list(
            ReportingPeriod.objects.filter(
                name__startswith="DEMO M10 FY ",
                period_type=PeriodType.ANNUAL,
            ).order_by("start_date")
        )
        if len(existing) >= 4:
            # These periods are owned solely by this command. Reuse the
            # original deterministic window on every subsequent run.
            return {"actual": existing[:3], "target": existing[-1]}

        # Prefer familiar recent years. If a local database already owns any
        # of them, use an unused historical block rather than modifying it.
        candidates = [2021, 2022, 2023]
        target_year = 2027
        if not all(self._annual_is_free(year) for year in [*candidates, target_year]):
            for start_year in range(2000, 2021):
                proposal = [start_year, start_year + 1, start_year + 2]
                proposed_target = start_year + 5
                if all(self._annual_is_free(year) for year in [*proposal, proposed_target]):
                    candidates, target_year = proposal, proposed_target
                    break
            else:
                raise CommandError("Could not find an unused annual-period window for the M10 demo.")

        def get_period(year, *, label):
            return ReportingPeriod.objects.create(
                name=f"DEMO M10 FY {year}-{str(year + 1)[-2:]}",
                period_type=PeriodType.ANNUAL,
                start_date=date(year, 4, 1),
                end_date=date(year + 1, 3, 31),
                status=PeriodStatus.OPEN,
                is_active=True,
            )

        return {
            "actual": [get_period(year, label="actual") for year in candidates],
            "target": get_period(target_year, label="target"),
        }

    def _datapoints(self):
        energy = Module.objects.get(code="energy")
        water = Module.objects.get(code="water")
        waste = Module.objects.get(code="waste")
        social = Module.objects.get(code="social")
        categories = {
            "energy": DatapointCategory.objects.get(code="ENERGY_CONSUMPTION"),
            "water": DatapointCategory.objects.get(code="WATER_CONSUMPTION"),
            "waste": DatapointCategory.objects.get(code="WASTE"),
            "workforce": DatapointCategory.objects.get_or_create(
                code="M10_DEMO_WORKFORCE", defaults={"name": "DEMO Workforce", "module": social}
            )[0],
        }
        families = {code: UnitFamily.objects.get(code=code) for code in ("ENERGY", "VOLUME", "MASS")}
        units = {code: Unit.objects.get(code=code) for code in ("KWH", "M3", "TONNE")}

        definitions = {
            "renewable": ("ENERGY_RENEWABLE_CONSUMPTION", "Renewable energy consumption", categories["energy"], energy, families["ENERGY"], units["KWH"], CollectionLevel.ORG_NODE),
            "withdrawal": ("WATER_TOTAL_WITHDRAWAL", "Total water withdrawal", categories["water"], water, families["VOLUME"], units["M3"], CollectionLevel.FACILITY),
            "recycled": ("WATER_RECYCLED_REUSED", "Water recycled or reused", categories["water"], water, families["VOLUME"], units["M3"], CollectionLevel.FACILITY),
            "waste_recycled": ("WASTE_RECYCLED", "Waste recycled / recovered", categories["waste"], waste, families["MASS"], units["TONNE"], CollectionLevel.FACILITY),
        }
        for key, (code, label, category, module, family, unit, level) in definitions.items():
            existing = Datapoint.objects.filter(code=code).first()
            if existing:
                compatible = (
                    existing.data_type == DatapointDataType.DECIMAL
                    and existing.unit_family_id == family.id
                    and existing.default_unit_id == unit.id
                    # M4's Module relation uses its stable module code as
                    # the persisted key, not Module's UUID identity.
                    and existing.module_id == module.code
                    and existing.collection_level == level
                )
                if not compatible:
                    raise CommandError(
                        f"Canonical datapoint {code} exists but is incompatible with the M10 demo "
                        "(type, module, unit family/default unit, or collection level differs)."
                    )
                continue
            Datapoint.objects.create(
                code=code, label=label, description="Controlled M10 demo datapoint.",
                category=category, module=module, data_type=DatapointDataType.DECIMAL,
                unit_family=family, default_unit=unit, collection_level=level,
                frequency=CollectionFrequency.ANNUAL, is_required=False,
                validation_metadata={"min": "0", "decimal_places": 4}, is_active=True,
            )
        # The workforce example is present for catalog/KPI selection even
        # though this visual demo concentrates its real trajectory data on
        # environmental direct-capture metrics.
        workforce = Datapoint.objects.filter(code="WORKFORCE_FEMALE_COUNT").first()
        if workforce is None:
            Datapoint.objects.create(
                code="WORKFORCE_FEMALE_COUNT",
                **{
                "label": "Female employees / workers count", "description": "Controlled M10 demo datapoint.",
                "category": categories["workforce"], "module": social, "data_type": DatapointDataType.INTEGER,
                "collection_level": CollectionLevel.ORG_NODE, "frequency": CollectionFrequency.ANNUAL,
                "is_required": False, "validation_metadata": {"min": "0"}, "is_active": True,
                },
            )
        return {
            "water": Datapoint.objects.get(code="WATER_TOTAL_WITHDRAWAL"),
            "water_consumption": Datapoint.objects.get(code="WATER_TOTAL_CONSUMPTION"),
            "water_recycled": Datapoint.objects.get(code="WATER_RECYCLED_REUSED"),
            "energy": Datapoint.objects.get(code="ENERGY_TOTAL_CONSUMPTION"),
            "renewable": Datapoint.objects.get(code="ENERGY_RENEWABLE_CONSUMPTION"),
            "waste": Datapoint.objects.get(code="WASTE_GENERATED"),
        }

    def _seed_approved_values(self, datapoints, periods, org_node, maker, reviewer):
        values = {
            "water": ("120000", "112500", "106000"),
            "water_consumption": ("90000", "84000", "79000"),
            "water_recycled": ("25000", "30000", "38000"),
            "energy": ("2500000", "2380000", "2260000"),
            "renewable": ("500000", "720000", "950000"),
            # Existing M4 WASTE_GENERATED stores integer kilograms. The target
            # later displays tonnes via canonical M4 conversion.
            "waste": ("600000", "555000", "495000"),
        }
        for key, datapoint in datapoints.items():
            for period, value in zip(periods, values[key], strict=True):
                request = DataRequest.objects.filter(
                    datapoint=datapoint, org_node=org_node, reporting_period=period
                ).select_related("submission").first()
                if request is None:
                    request = DataCaptureLifecycleService.create_request(
                        actor=reviewer, datapoint=datapoint, org_node=org_node,
                        reporting_period=period, assignee=maker,
                        instructions="DEMO M10 approved value for target trajectory.",
                    )
                submission = request.submission
                if submission.status == SubmissionStatus.APPROVED:
                    continue
                if submission.status == SubmissionStatus.SUBMITTED:
                    DataCaptureLifecycleService.approve(submission, actor=reviewer)
                    continue
                if submission.status == SubmissionStatus.REJECTED:
                    DataCaptureLifecycleService.reopen(submission, actor=reviewer, reason="Restore controlled demo value.")
                    submission.refresh_from_db()
                kwargs = {"unit": datapoint.default_unit}
                kwargs["integer_value" if datapoint.data_type == DatapointDataType.INTEGER else "decimal_value"] = Decimal(value) if datapoint.data_type != DatapointDataType.INTEGER else int(value)
                DataCaptureLifecycleService.save_scalar_answer(submission, actor=maker, **kwargs)
                DataCaptureLifecycleService.submit(submission, actor=maker)
                DataCaptureLifecycleService.approve(submission, actor=reviewer)

    def _seed_goals(self, company, datapoints, periods, org_node, owner):
        topics = {topic.name: topic for topic in MaterialTopic.objects.filter(is_active=True)}
        scenarios = (
            ("Water Stewardship", "Reduce freshwater withdrawal at the demo plant while supporting efficient operations.", "Resource Use & Circular Economy", "water", "Total water withdrawal", KPIDirection.REDUCE, Decimal("120000"), Decimal("90000"), TargetBasis.PRIOR_YEAR_ACTUAL, "M3"),
            ("Energy Efficiency", "Reduce direct energy consumption through operational efficiency.", "Climate Change", "energy", "Total energy consumption", KPIDirection.REDUCE, Decimal("2500000"), Decimal("2000000"), TargetBasis.PRIOR_YEAR_ACTUAL, "KWH"),
            ("Renewable Energy Adoption", "Increase renewable electricity consumption through onsite and contracted supply.", "Climate Change", "renewable", "Renewable energy consumption", KPIDirection.INCREASE, Decimal("500000"), Decimal("1500000"), TargetBasis.MANAGEMENT_COMMITMENT, "KWH"),
            ("Operational Waste Reduction", "Reduce total operational waste through better segregation and yield management.", None, "waste", "Total waste generated", KPIDirection.REDUCE, Decimal("600"), Decimal("420"), TargetBasis.PRIOR_YEAR_ACTUAL, "TONNE"),
        )
        for index, (name, description, topic_name, key, kpi_name, direction, baseline, endpoint, basis, unit_code) in enumerate(scenarios, start=1):
            goal, _ = Goal.objects.update_or_create(
                name=f"DEMO M10 — {name}", created_by=owner,
                defaults={"company": company, "description": description, "material_topic": topics.get(topic_name), "status": GoalStatus.ACTIVE, "owner": owner},
            )
            datapoint = datapoints[key]
            kpi, _ = KPI.objects.update_or_create(
                goal=goal, code=f"demo.{key}",
                defaults={
                    "name": kpi_name, "description": datapoint.label,
                    "metric_source_type": MetricSourceType.DATAPOINT, "datapoint": datapoint,
                    "direction": direction, "aggregation": KPIAggregation.SUM,
                    "display_order": index, "is_active": True,
                },
            )
            unit = Unit.objects.get(code=unit_code)
            change = (
                ((endpoint - baseline) / baseline * Decimal("100")).quantize(Decimal("0.0001"))
                if baseline else None
            )
            Target.objects.update_or_create(
                kpi=kpi, org_node=org_node, target_period=periods["target"],
                defaults={
                    "baseline_period": periods["actual"][0], "baseline_value": baseline,
                    "baseline_unit": unit, "baseline_source": BaselineSource.SYSTEM_DATA,
                    "target_value": endpoint, "target_unit": unit, "target_type": TargetType.ABSOLUTE,
                    "change_percentage": change, "owner": owner, "status": TargetStatus.ACTIVE,
                    "basis": basis, "source_reference": "DEMO M10 planning fixture",
                    "methodology": "Straight-line trajectory between frozen baseline and target endpoint.",
                    "rationale": description, "created_by": owner,
                },
            )

        # Keep multiple direct-capture KPIs on a single goal so the demo also
        # exercises the KPI selector, chart switching, and overflow behavior.
        water_goal = Goal.objects.get(name="DEMO M10 — Water Stewardship", created_by=owner)
        for display_order, key, name, direction, baseline, endpoint, basis in (
            (2, "water_consumption", "Total water consumption", KPIDirection.REDUCE, Decimal("90000"), Decimal("65000"), TargetBasis.PRIOR_YEAR_ACTUAL),
            (3, "water_recycled", "Water recycled or reused", KPIDirection.INCREASE, Decimal("25000"), Decimal("70000"), TargetBasis.MANAGEMENT_COMMITMENT),
        ):
            datapoint = datapoints[key]
            kpi, _ = KPI.objects.update_or_create(
                goal=water_goal,
                code=f"demo.{key}",
                defaults={
                    "name": name,
                    "description": datapoint.label,
                    "metric_source_type": MetricSourceType.DATAPOINT,
                    "datapoint": datapoint,
                    "direction": direction,
                    "aggregation": KPIAggregation.SUM,
                    "display_order": display_order,
                    "is_active": True,
                },
            )
            change = ((endpoint - baseline) / baseline * Decimal("100")).quantize(Decimal("0.0001"))
            Target.objects.update_or_create(
                kpi=kpi,
                org_node=org_node,
                target_period=periods["target"],
                defaults={
                    "baseline_period": periods["actual"][0],
                    "baseline_value": baseline,
                    "baseline_unit": Unit.objects.get(code="M3"),
                    "baseline_source": BaselineSource.SYSTEM_DATA,
                    "target_value": endpoint,
                    "target_unit": Unit.objects.get(code="M3"),
                    "target_type": TargetType.ABSOLUTE,
                    "change_percentage": change,
                    "owner": owner,
                    "status": TargetStatus.ACTIVE,
                    "basis": basis,
                    "source_reference": "DEMO M10 planning fixture",
                    "methodology": "Straight-line trajectory between frozen baseline and target endpoint.",
                    "rationale": water_goal.description,
                    "created_by": owner,
                },
            )
