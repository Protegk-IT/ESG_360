from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.organizations.models import OrgNode


class Command(BaseCommand):
    help = "Seed organization hierarchy."

    def handle(self, *args, **options):
        company = Company.objects.first()

        if not company:
            self.stdout.write(
                self.style.ERROR("No company found. Please create a company first.")
            )
            return

        root = OrgNode.objects.filter(
            company=company,
            node_type="LEGAL_ENTITY",
            parent__isnull=True,
        ).first()

        if not root:
            self.stdout.write(
                self.style.ERROR("Root LEGAL_ENTITY node not found.")
            )
            return

        # -------------------------
        # Business Unit
        # -------------------------

        precision, _ = OrgNode.objects.get_or_create(
            company=company,
            code="precision",
            defaults={
                "parent": root,
                "name": "Precision Components",
                "node_type": "BUSINESS_UNIT",
            },
        )

        electricals, _ = OrgNode.objects.get_or_create(
            company=company,
            code="electricals",
            defaults={
                "parent": root,
                "name": "Electricals",
                "node_type": "BUSINESS_UNIT",
            },
        )

        # -------------------------
        # Region
        # -------------------------

        west_region, _ = OrgNode.objects.get_or_create(
            company=company,
            code="west",
            defaults={
                "parent": precision,
                "name": "West Region",
                "node_type": "REGION",
            },
        )

        # -------------------------
        # Facilities
        # -------------------------

        OrgNode.objects.get_or_create(
            company=company,
            code="chakan",
            defaults={
                "parent": west_region,
                "name": "Chakan Plant",
                "node_type": "FACILITY",
                "facility_type": "Manufacturing Plant",
                "address": "Chakan MIDC, Pune",
                "grid_region": "Western Grid",
                "water_stressed_area": False,
            },
        )

        OrgNode.objects.get_or_create(
            company=company,
            code="bhiwandi",
            defaults={
                "parent": west_region,
                "name": "Bhiwandi Warehouse",
                "node_type": "FACILITY",
                "facility_type": "Warehouse",
                "address": "Bhiwandi, Maharashtra",
                "grid_region": "Western Grid",
                "water_stressed_area": False,
            },
        )

        OrgNode.objects.get_or_create(
            company=company,
            code="hosur",
            defaults={
                "parent": precision,
                "name": "Hosur Plant",
                "node_type": "FACILITY",
                "facility_type": "Manufacturing Plant",
                "address": "Hosur, Tamil Nadu",
                "grid_region": "Southern Grid",
                "water_stressed_area": False,
            },
        )

        OrgNode.objects.get_or_create(
            company=company,
            code="pantnagar",
            defaults={
                "parent": electricals,
                "name": "Pantnagar Plant",
                "node_type": "FACILITY",
                "facility_type": "Manufacturing Plant",
                "address": "Pantnagar, Uttarakhand",
                "grid_region": "Northern Grid",
                "water_stressed_area": False,
            },
        )

        self.stdout.write(
            self.style.SUCCESS("Organization hierarchy seeded successfully.")
        )