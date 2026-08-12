from django.core.management.base import BaseCommand

from apps.modules.models import Module


MODULES = [
    {
        "code": "company",
        "name": "Company",
        "description": "Company and organizational management.",
        "esg_pillar": "PLATFORM",
        "icon": "building",
        "is_core": True,
        "is_enabled": True,
        "display_order": 1,
    },
    {
        "code": "org",
        "name": "Organization",
        "description": "Organization structure and hierarchy management.",
        "esg_pillar": "PLATFORM",
        "icon": "network",
        "is_core": True,
        "is_enabled": True,
        "display_order": 2,
    },
    {
        "code": "user",
        "name": "Users",
        "description": "User, role, and access management.",
        "esg_pillar": "PLATFORM",
        "icon": "users",
        "is_core": True,
        "is_enabled": True,
        "display_order": 3,
    },
    {
        "code": "period",
        "name": "Reporting Periods",
        "description": "Reporting period and reporting calendar management.",
        "esg_pillar": "PLATFORM",
        "icon": "calendar",
        "is_core": True,
        "is_enabled": True,
        "display_order": 4,
    },
    {
        "code": "energy",
        "name": "Energy",
        "description": "Energy data collection and management.",
        "esg_pillar": "E",
        "icon": "zap",
        "is_core": False,
        "is_enabled": False,
        "display_order": 10,
    },
    {
        "code": "emissions",
        "name": "Emissions",
        "description": "Greenhouse gas emissions data and management.",
        "esg_pillar": "E",
        "icon": "cloud",
        "is_core": False,
        "is_enabled": False,
        "display_order": 11,
    },
    {
        "code": "water",
        "name": "Water",
        "description": "Water consumption and management.",
        "esg_pillar": "E",
        "icon": "droplets",
        "is_core": False,
        "is_enabled": False,
        "display_order": 12,
    },
    {
        "code": "waste",
        "name": "Waste",
        "description": "Waste generation and management.",
        "esg_pillar": "E",
        "icon": "recycle",
        "is_core": False,
        "is_enabled": False,
        "display_order": 13,
    },
    {
        "code": "social",
        "name": "Social",
        "description": "Social sustainability data and management.",
        "esg_pillar": "S",
        "icon": "heart",
        "is_core": False,
        "is_enabled": False,
        "display_order": 20,
    },
    {
        "code": "governance",
        "name": "Governance",
        "description": "Governance data and management.",
        "esg_pillar": "G",
        "icon": "landmark",
        "is_core": False,
        "is_enabled": False,
        "display_order": 30,
    },
    {
        "code": "supplier",
        "name": "Supplier",
        "description": "Supplier sustainability and supply chain management.",
        "esg_pillar": "S",
        "icon": "truck",
        "is_core": False,
        "is_enabled": False,
        "display_order": 40,
    },
    {
        "code": "materiality",
        "name": "Materiality",
        "description": "Materiality assessment and topic management.",
        "esg_pillar": "PLATFORM",
        "icon": "layers",
        "is_core": False,
        "is_enabled": False,
        "display_order": 50,
    },
    {
        "code": "report",
        "name": "Reporting",
        "description": "ESG reporting and report generation.",
        "esg_pillar": "PLATFORM",
        "icon": "file-text",
        "is_core": False,
        "is_enabled": False,
        "display_order": 60,
    },
]


class Command(BaseCommand):
    help = "Seed the canonical ESG 360 module registry."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for module_data in MODULES:
            code = module_data["code"]

            defaults = {
                "name": module_data["name"],
                "description": module_data["description"],
                "esg_pillar": module_data["esg_pillar"],
                "icon": module_data["icon"],
                "is_core": module_data["is_core"],
                "display_order": module_data["display_order"],
            }

            module, created = Module.objects.update_or_create(
                code=code,
                defaults=defaults,
            )

            if created:
                module.is_enabled = module_data["is_enabled"]
                module.save()

                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created module: {module.code}"
                    )
                )
            else:
                updated_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Updated module metadata: {module.code}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Module seeding completed. "
                f"Created: {created_count}, "
                f"Updated: {updated_count}"
            )
        )