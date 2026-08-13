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
        "code": "organization",
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
        "code": "reporting_period",
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
        "display_order": 100,
    },
    {
        "code": "emissions",
        "name": "Emissions",
        "description": "Greenhouse gas emissions data and management.",
        "esg_pillar": "E",
        "icon": "cloud",
        "is_core": False,
        "is_enabled": False,
        "display_order": 101,
    },
    {
        "code": "water",
        "name": "Water",
        "description": "Water consumption and management.",
        "esg_pillar": "E",
        "icon": "droplets",
        "is_core": False,
        "is_enabled": False,
        "display_order": 102,
    },
    {
        "code": "waste",
        "name": "Waste",
        "description": "Waste generation and management.",
        "esg_pillar": "E",
        "icon": "recycle",
        "is_core": False,
        "is_enabled": False,
        "display_order": 103,
    },
    {
        "code": "social",
        "name": "Social",
        "description": "Social sustainability data and management.",
        "esg_pillar": "S",
        "icon": "heart",
        "is_core": False,
        "is_enabled": False,
        "display_order": 110,
    },
    {
        "code": "governance",
        "name": "Governance",
        "description": "Governance data and management.",
        "esg_pillar": "G",
        "icon": "landmark",
        "is_core": False,
        "is_enabled": False,
        "display_order": 120,
    },
    {
        "code": "supplier",
        "name": "Supplier",
        "description": "Supplier sustainability and supply chain management.",
        "esg_pillar": "S",
        "icon": "truck",
        "is_core": False,
        "is_enabled": False,
        "display_order": 130,
    },
    {
        "code": "materiality",
        "name": "Materiality",
        "description": "Materiality assessment and topic management.",
        "esg_pillar": "PLATFORM",
        "icon": "layers",
        "is_core": False,
        "is_enabled": False,
        "display_order": 140,
    },
    {
        "code": "report",
        "name": "Reporting",
        "description": "ESG reporting and report generation.",
        "esg_pillar": "PLATFORM",
        "icon": "file-text",
        "is_core": False,
        "is_enabled": False,
        "display_order": 150,
    },
    # These codes are already active in the stabilized permission contract.
    # Keep them in the registry even when their feature module has not yet
    # been implemented, so ``<module>.<action>`` and assignment module scopes
    # always resolve to one canonical catalog entry.
    {
        "code": "country",
        "name": "Countries",
        "description": "Country reference data management.",
        "esg_pillar": "PLATFORM",
        "icon": "globe",
        "is_core": False,
        "is_enabled": True,
        "display_order": 5,
    },
    {
        "code": "state",
        "name": "States",
        "description": "State reference data management.",
        "esg_pillar": "PLATFORM",
        "icon": "map",
        "is_core": False,
        "is_enabled": True,
        "display_order": 6,
    },
    {
        "code": "city",
        "name": "Cities",
        "description": "City reference data management.",
        "esg_pillar": "PLATFORM",
        "icon": "map-pin",
        "is_core": False,
        "is_enabled": True,
        "display_order": 7,
    },
    {
        "code": "department",
        "name": "Departments",
        "description": "Company department management.",
        "esg_pillar": "PLATFORM",
        "icon": "building-2",
        "is_core": False,
        "is_enabled": True,
        "display_order": 8,
    },
    {
        "code": "role",
        "name": "Roles",
        "description": "Role and permission-bundle administration.",
        "esg_pillar": "PLATFORM",
        "icon": "shield",
        "is_core": False,
        "is_enabled": True,
        "display_order": 9,
    },
    {
        "code": "permission",
        "name": "Permissions",
        "description": "Permission catalog visibility.",
        "esg_pillar": "PLATFORM",
        "icon": "key-round",
        "is_core": False,
        "is_enabled": True,
        "display_order": 10,
    },
    {
        "code": "dashboard",
        "name": "Dashboard",
        "description": "Platform dashboard and summary metrics.",
        "esg_pillar": "PLATFORM",
        "icon": "layout-dashboard",
        "is_core": False,
        "is_enabled": True,
        "display_order": 11,
    },
    {
        "code": "activity_log",
        "name": "Activity Log",
        "description": "Auditable platform activity history.",
        "esg_pillar": "PLATFORM",
        "icon": "history",
        "is_core": False,
        "is_enabled": True,
        "display_order": 12,
    },
    {
        "code": "datapoint",
        "name": "Datapoints",
        "description": "ESG datapoint catalog management.",
        "esg_pillar": "PLATFORM",
        "icon": "database",
        "is_core": False,
        "is_enabled": False,
        "display_order": 20,
    },
    {
        "code": "emission_factor",
        "name": "Emission Factors",
        "description": "Emission-factor catalog management.",
        "esg_pillar": "E",
        "icon": "calculator",
        "is_core": False,
        "is_enabled": False,
        "display_order": 21,
    },
    {
        "code": "framework_mapping",
        "name": "Framework Mapping",
        "description": "Sustainability-framework mapping management.",
        "esg_pillar": "PLATFORM",
        "icon": "git-merge",
        "is_core": False,
        "is_enabled": False,
        "display_order": 22,
    },
    {
        "code": "data",
        "name": "Data Collection",
        "description": "ESG data entry, submission, and approval.",
        "esg_pillar": "PLATFORM",
        "icon": "clipboard-input",
        "is_core": False,
        "is_enabled": False,
        "display_order": 23,
    },
    {
        "code": "evidence",
        "name": "Evidence",
        "description": "Evidence upload and review.",
        "esg_pillar": "PLATFORM",
        "icon": "paperclip",
        "is_core": False,
        "is_enabled": False,
        "display_order": 24,
    },
    {
        "code": "disclosure",
        "name": "Disclosures",
        "description": "Disclosure assignment and response workflows.",
        "esg_pillar": "PLATFORM",
        "icon": "file-check",
        "is_core": False,
        "is_enabled": False,
        "display_order": 25,
    },
    {
        "code": "target",
        "name": "Targets",
        "description": "Sustainability-target management.",
        "esg_pillar": "PLATFORM",
        "icon": "target",
        "is_core": False,
        "is_enabled": False,
        "display_order": 26,
    },
    {
        "code": "audit",
        "name": "Audit",
        "description": "Audit query and response workflows.",
        "esg_pillar": "PLATFORM",
        "icon": "search-check",
        "is_core": False,
        "is_enabled": False,
        "display_order": 27,
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

            module, created = Module.objects.get_or_create(
                code=code,
                defaults={
                    **defaults,
                    "is_enabled": module_data["is_enabled"],
                },
            )

            if created:

                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created module: {module.code}"
                    )
                )
            else:
                for field, value in defaults.items():
                    setattr(module, field, value)

                # Enabled state is deployment configuration for optional
                # modules and must survive seed reruns. Core modules are the
                # exception: their invariant requires them to remain enabled.
                if module.is_core:
                    module.is_enabled = True

                module.save()
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
