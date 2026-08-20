from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.frameworks.models import (
    Framework,
    FrameworkVersion,
    FrameworkNode,
    DatapointMapping,
)

from apps.datapoints.models import Datapoint


class Command(BaseCommand):
    help = (
        "Create representative framework-to-M4 datapoint mappings "
        "for development and testing."
    )

    @transaction.atomic
    def handle(self, *args, **options):

        self.stdout.write(
            self.style.NOTICE(
                "Starting framework datapoint mapping seed..."
            )
        )

        framework = self.get_framework()
        version = self.get_framework_version(framework)

        self.seed_mappings(version)

        self.stdout.write(
            self.style.SUCCESS(
                "Framework datapoint mapping seed completed successfully."
            )
        )

    # ---------------------------------------------------------
    # FRAMEWORK
    # ---------------------------------------------------------

    def get_framework(self):
        """
        Get the framework created by seed_frameworks.

        We intentionally do not create the framework here.
        Framework content belongs to seed_frameworks.
        """

        try:
            return Framework.objects.get(code="GRI")

        except Framework.DoesNotExist as exc:
            raise CommandError(
                "Framework GRI does not exist. "
                "Run 'python manage.py seed_frameworks' first."
            ) from exc

    # ---------------------------------------------------------
    # FRAMEWORK VERSION
    # ---------------------------------------------------------

    def get_framework_version(self, framework):
        """
        Get the representative GRI version.

        Named get_framework_version instead of get_version
        to avoid overriding Django BaseCommand.get_version().
        """

        try:
            return FrameworkVersion.objects.get(
                framework=framework,
                version_code="GRI-2021",
            )

        except FrameworkVersion.DoesNotExist as exc:
            raise CommandError(
                "Framework version GRI-2021 does not exist. "
                "Run 'python manage.py seed_frameworks' first."
            ) from exc

    # ---------------------------------------------------------
    # MAPPINGS
    # ---------------------------------------------------------

    def seed_mappings(self, version):
        """
        Create representative M7 → M4 mappings.

        These mappings are intentionally small and are only
        representative development/test data.

        The complete official GRI mapping population is
        outside the scope of this seed.
        """

        mappings = [
            {
                "node_code": "302-1",
                "datapoint_code": "ENERGY_TOTAL_CONSUMPTION",
                "mapping_type": DatapointMapping.MappingType.DIRECT,
                "aggregation": DatapointMapping.Aggregation.NONE,
                "is_primary": True,
                "confidence": DatapointMapping.Confidence.PROVISIONAL,
                "mapping_note": (
                    "Representative development mapping. "
                    "Official framework-to-datapoint mapping "
                    "requires content review."
                ),
            },
            {
                "node_code": "302-2",
                "datapoint_code": "ENERGY_DESCRIPTION",
                "mapping_type": DatapointMapping.MappingType.NARRATIVE,
                "aggregation": DatapointMapping.Aggregation.NONE,
                "is_primary": True,
                "confidence": DatapointMapping.Confidence.PROVISIONAL,
                "mapping_note": (
                    "Representative development mapping for "
                    "narrative information. Official framework-to-"
                    "datapoint mapping requires content review."
                ),
            },
        ]

        for mapping_data in mappings:

            node = self.get_node(
                version=version,
                code=mapping_data["node_code"],
            )

            datapoint = self.get_datapoint(
                code=mapping_data["datapoint_code"],
            )

            mapping, created = (
                DatapointMapping.objects.update_or_create(
                    framework_node=node,
                    datapoint=datapoint,
                    defaults={
                        "mapping_type": mapping_data["mapping_type"],
                        "aggregation": mapping_data["aggregation"],
                        "transform_expression": "",
                        "is_primary": mapping_data["is_primary"],
                        "confidence": mapping_data["confidence"],
                        "mapping_note": mapping_data["mapping_note"],
                        "reviewed_at": None,
                    },
                )
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created mapping: "
                        f"{node.code} -> {datapoint.code}"
                    )
                )
            else:
                self.stdout.write(
                    f"  Updated mapping: "
                    f"{node.code} -> {datapoint.code}"
                )

    # ---------------------------------------------------------
    # FRAMEWORK NODE
    # ---------------------------------------------------------

    def get_node(self, *, version, code):
        """
        Get a framework node by its stable code.

        Node codes are unique within a framework version.
        """

        try:
            return FrameworkNode.objects.get(
                framework_version=version,
                code=code,
            )

        except FrameworkNode.DoesNotExist as exc:
            raise CommandError(
                f"Framework node '{code}' does not exist in "
                f"framework version '{version.version_code}'. "
                "Run 'python manage.py seed_frameworks' first."
            ) from exc

    # ---------------------------------------------------------
    # M4 DATAPOINT
    # ---------------------------------------------------------

    def get_datapoint(self, *, code):
        """
        Get the canonical M4 datapoint by stable code.

        M7 never creates or duplicates datapoints.
        """

        try:
            return Datapoint.objects.get(
                code=code,
            )

        except Datapoint.DoesNotExist as exc:
            raise CommandError(
                f"M4 datapoint '{code}' does not exist. "
                "Run 'python manage.py seed_datapoints' first."
            ) from exc