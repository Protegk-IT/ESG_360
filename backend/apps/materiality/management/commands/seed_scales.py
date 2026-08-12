from django.core.management.base import BaseCommand

from apps.materiality.models import ScaleDefinition, ScaleOption


class Command(BaseCommand):
    help = "Seed default materiality assessment scales."

    SCALES = {
        "IMPACT": {
            "name": "Impact Scale",
            "options": [
                {
                    "value": 1,
                    "label": "No impact",
                    "description": "No meaningful effect",
                },
                {
                    "value": 2,
                    "label": "Low impact",
                    "description": "Small, localised effect, easily managed",
                },
                {
                    "value": 3,
                    "label": "Medium impact",
                    "description": (
                        "Noticeable effect on the surrounding area or group"
                    ),
                },
                {
                    "value": 4,
                    "label": "High impact",
                    "description": (
                        "Substantial effect requiring active management"
                    ),
                },
                {
                    "value": 5,
                    "label": "Very high impact",
                    "description": "Severe or irreversible effect",
                },
            ],
        },
        "STAKEHOLDER_IMPORTANCE": {
            "name": "Stakeholder Importance Scale",
            "options": [
                {
                    "value": 1,
                    "label": "No importance",
                    "description": "",
                },
                {
                    "value": 2,
                    "label": "Low importance",
                    "description": "",
                },
                {
                    "value": 3,
                    "label": "Medium importance",
                    "description": "",
                },
                {
                    "value": 4,
                    "label": "High importance",
                    "description": "",
                },
                {
                    "value": 5,
                    "label": "Very high importance",
                    "description": "",
                },
            ],
        },
        "FINANCIAL": {
            "name": "Financial Scale",
            "options": [
                {
                    "value": 1,
                    "label": "Not material",
                    "description": "No cost or revenue exposure",
                },
                {
                    "value": 2,
                    "label": "Minor",
                    "description": "Small variance, easily absorbed",
                },
                {
                    "value": 3,
                    "label": "Moderate",
                    "description": (
                        "Noticeable cost or revenue impact in some years"
                    ),
                },
                {
                    "value": 4,
                    "label": "Significant",
                    "description": (
                        "Material cost increase or operational risk"
                    ),
                },
                {
                    "value": 5,
                    "label": "Critical",
                    "description": (
                        "Could halt operations or require major capital spend"
                    ),
                },
            ],
        },
    }

    def handle(self, *args, **options):

        for dimension, scale_data in self.SCALES.items():

            scale, scale_created = ScaleDefinition.objects.get_or_create(
                assessment=None,
                dimension=dimension,
                defaults={
                    "name": scale_data["name"],
                },
            )

            if scale_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created default {dimension} scale."
                    )
                )
            else:
                self.stdout.write(
                    f"Default {dimension} scale already exists."
                )

            for option_data in scale_data["options"]:

                option, option_created = ScaleOption.objects.get_or_create(
                    scale=scale,
                    value=option_data["value"],
                    defaults={
                        "label": option_data["label"],
                        "description": option_data["description"],
                    },
                )

                if option_created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Created option {option.value}: "
                            f"{option.label}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Default materiality scales seeded successfully."
            )
        )