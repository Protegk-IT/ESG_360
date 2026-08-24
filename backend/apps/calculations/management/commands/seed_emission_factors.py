from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.calculations.models import (
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)
from apps.datapoints.models import Unit


class Command(BaseCommand):
    help = (
        "Seed representative M6 emission-factor sources, "
        "factors and calculation rules."
    )

    # ---------------------------------------------------------
    # DEMO / TEST DATA ONLY
    # ---------------------------------------------------------
    #
    # These values are intentionally representative.
    # They are NOT official emission-factor values.
    #
    # Replace them with reviewed source data in a future
    # production factor-library import.
    # ---------------------------------------------------------

    SOURCE = {
        "code": "demo_m6_factor_set",
        "name": "M6 Representative Factor Set",
        "publisher": "ESG 360 Demo",
        "version": "1.0",
        "source_reference": (
            "Representative test data only; "
            "not an official emission-factor publication."
        ),
        "source_url": "",
        "is_active": True,
    }

    FACTORS = [
    {
        "code": "demo_grid_electricity",
        "activity_key": "electricity_consumption",
        "input_unit_code": "KWH",
        "output_unit_code": "KG",
        "factor_value": Decimal("0.500000000000000"),
        "geography": "DEMO",
        "effective_from": None,
        "effective_to": None,
        "is_active": True,
        "notes": (
            "Representative M6 test factor only. "
            "Output represents calculated emissions mass. "
            "Not an official emission factor."
        ),
    },
    {
        "code": "demo_fuel_combustion",
        "activity_key": "fuel_combustion",
        "input_unit_code": "L",
        "output_unit_code": "KG",
        "factor_value": Decimal("2.500000000000000"),
        "geography": "DEMO",
        "effective_from": None,
        "effective_to": None,
        "is_active": True,
        "notes": (
            "Representative M6 test factor only. "
            "Output represents calculated emissions mass. "
            "Not an official emission factor."
        ),
    },
]

    CALCULATION_RULES = [
        {
            "code": "demo_activity_times_factor",
            "name": "Activity Quantity × Emission Factor",
            "description": (
                "Representative declarative rule describing "
                "the standard M6 activity-factor calculation."
            ),
            "rule_metadata": {
                "operation": "multiply",
                "input": "activity_quantity",
                "factor": "emission_factor",
            },
            "is_active": True,
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Seeding M6 emission-factor foundation..."
            )
        )

        source = self._seed_source()

        self._seed_factors(source)

        self._seed_calculation_rules()

        self.stdout.write(
            self.style.SUCCESS(
                "M6 emission-factor seed completed successfully."
            )
        )

    # ---------------------------------------------------------
    # SOURCE
    # ---------------------------------------------------------

    def _seed_source(self):
        source, created = EmissionFactorSource.objects.get_or_create(
            code=self.SOURCE["code"],
            version=self.SOURCE["version"],
            defaults=self.SOURCE,
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created factor source: {source.code}"
                )
            )
        else:
            updated = False

            for field in [
                "name",
                "publisher",
                "source_reference",
                "source_url",
                "is_active",
            ]:
                value = self.SOURCE[field]

                if getattr(source, field) != value:
                    setattr(source, field, value)
                    updated = True

            if updated:
                source.save()

                self.stdout.write(
                    self.style.WARNING(
                        f"Updated factor source: {source.code}"
                    )
                )
            else:
                self.stdout.write(
                    f"Factor source already exists: {source.code}"
                )

        return source

    # ---------------------------------------------------------
    # FACTORS
    # ---------------------------------------------------------

    def _seed_factors(self, source):
        for factor_data in self.FACTORS:
            input_unit = self._get_unit(
                factor_data["input_unit_code"]
            )

            output_unit = self._get_unit(
                factor_data["output_unit_code"]
            )

            defaults = {
                "activity_key": factor_data["activity_key"],
                "input_unit": input_unit,
                "output_unit": output_unit,
                "factor_value": factor_data["factor_value"],
                "geography": factor_data["geography"],
                "effective_from": factor_data["effective_from"],
                "effective_to": factor_data["effective_to"],
                "is_active": factor_data["is_active"],
                "notes": factor_data["notes"],
            }

            factor, created = EmissionFactor.objects.update_or_create(
                source=source,
                code=factor_data["code"],
                defaults=defaults,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created factor: {factor.code}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated factor: {factor.code}"
                    )
                )

    # ---------------------------------------------------------
    # CALCULATION RULES
    # ---------------------------------------------------------

    def _seed_calculation_rules(self):
        for rule_data in self.CALCULATION_RULES:
            rule, created = CalculationRule.objects.update_or_create(
                code=rule_data["code"],
                defaults={
                    "name": rule_data["name"],
                    "description": rule_data["description"],
                    "rule_metadata": rule_data["rule_metadata"],
                    "is_active": rule_data["is_active"],
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created calculation rule: {rule.code}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated calculation rule: {rule.code}"
                    )
                )

    # ---------------------------------------------------------
    # UNIT LOOKUP
    # ---------------------------------------------------------

    def _get_unit(self, code):
        try:
            return Unit.objects.get(
                code=code,
                is_active=True,
            )
        except Unit.DoesNotExist:
            raise CommandError(
                (
                    f"Required M4 Unit '{code}' does not exist "
                    "or is inactive. "
                    "M6 seed data does not create or duplicate "
                    "M4 units."
                )
            )