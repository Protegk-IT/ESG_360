"""Seed the supported ESG360 demo foundation in one idempotent command."""

from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.companies.models import City, Company, Country, Department, State
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod, Status


class Command(BaseCommand):
    help = "Seed the supported Sahyadri demo company, hierarchy, departments, periods, and platform reference data."

    def handle(self, *args, **options):
        # These commands own their reference data and are independently
        # idempotent. Keep them outside the foundation transaction.
        for command in ("seed_locations", "seed_modules", "seed_rbac", "seed_materiality", "seed_scales"):
            call_command(command, verbosity=0)

        with transaction.atomic():
            india, maharashtra, pune = self._locations()
            company = self._company(india, maharashtra, pune)
            self._hierarchy(company, india)
            self._departments(company)
            self._periods()

        self.stdout.write(self.style.SUCCESS(
            "Demo foundation seeded: SAHY company, 8 organisation nodes, 7 departments, and reporting periods."
        ))

    def _locations(self):
        india, _ = Country.objects.get_or_create(
            iso_code="IN", defaults={"name": "India", "is_active": True}
        )
        # seed_locations supplies these states. get_or_create makes the demo
        # command robust for installations with a reduced location catalogue.
        states = {}
        for code, name in (("MH", "Maharashtra"), ("TN", "Tamil Nadu"), ("UK", "Uttarakhand")):
            states[code], _ = State.objects.get_or_create(
                country=india, state_code=code,
                defaults={"name": name, "is_active": True},
            )
        cities = {}
        for state_code, name in (
            ("MH", "Pune"), ("MH", "Chakan"), ("MH", "Bhiwandi"),
            ("TN", "Hosur"), ("UK", "Pantnagar"),
        ):
            cities[state_code, name], _ = City.objects.get_or_create(
                country=india, state=states[state_code], name=name,
                defaults={"is_active": True},
            )
        self.cities = cities
        self.states = states
        return india, states["MH"], cities["MH", "Pune"]

    def _company(self, country, state, city):
        company, _ = Company.objects.update_or_create(
            company_code="SAHY",
            defaults={
                "company_name": "Sahyadri Auto Components Ltd",
                "cin_number": "L28920MH2004PLC123456",
                "gst_number": "27AABCS1234C1Z5",
                "date_of_incorporation": date(2004, 3, 12),
                "ownership_form": "Public limited company",
                "listed_company": True,
                "stock_exchanges": "BSE, NSE",
                "paid_up_capital": "425000000.00",  # INR 42.5 crore
                "turnover": "18400000000.00",  # INR 1,840 crore
                "registered_address": "Plot 14, MIDC Industrial Area, Chakan, Pune, Maharashtra 410501",
                "corporate_address": "Sahyadri House, Senapati Bapat Road, Pune, Maharashtra 411016",
                "country": country, "state": state, "city": city,
                "contact_person": "Meera Kulkarni",
                "email": "investors@sahyadriauto.example",
                "mobile_number": "+919822011234",
                "website": "https://www.sahyadriauto.example",
                "employee_count": 3200,
                "financial_year_start_month": 4,
                "is_active": True,
            },
        )
        return company

    def _node(self, company, code, name, node_type, parent=None, **attrs):
        node, created = OrgNode.objects.get_or_create(
            company=company, code=code,
            defaults={"name": name, "node_type": node_type, "parent": parent, **attrs},
        )
        if not created:
            for field, value in {"name": name, "node_type": node_type, "parent": parent, **attrs}.items():
                setattr(node, field, value)
            node.save()
        return node

    def _hierarchy(self, company, country):
        # Company creation creates a root automatically; normalize it to the
        # documented code instead of attempting to create a second root.
        root = OrgNode.objects.get(company=company, parent__isnull=True, node_type="LEGAL_ENTITY")
        root.code = "SAHY"
        root.name = "Sahyadri Auto Components Ltd"
        root.save()
        precision = self._node(company, "BU-PREC", "Precision Components", "BUSINESS_UNIT", root)
        electricals = self._node(company, "BU-ELEC", "Electricals", "BUSINESS_UNIT", root)
        facility_defaults = {"ownership_percentage": "100.00", "operational_control": True, "consolidation_method": "FULL"}
        self._node(company, "HQ-PUN", "Corporate HQ — Pune", "FACILITY", root,
                   facility_type="Corporate office", address="Senapati Bapat Road, Pune, Maharashtra 411016",
                   grid_region="Maharashtra (WRLDC)", water_stressed_area=False,
                   country=country, state=self.states["MH"], city=self.cities["MH", "Pune"], **facility_defaults)
        self._node(company, "PLT-CHK", "Plant A — Chakan", "FACILITY", precision,
                   facility_type="Manufacturing — forging & machining", address="MIDC Industrial Area, Chakan, Maharashtra",
                   grid_region="Maharashtra (WRLDC)", water_stressed_area=True,
                   country=country, state=self.states["MH"], city=self.cities["MH", "Chakan"], **facility_defaults)
        self._node(company, "PLT-HSR", "Plant B — Hosur", "FACILITY", precision,
                   facility_type="Manufacturing — assembly", address="Hosur, Tamil Nadu",
                   grid_region="Tamil Nadu (SRLDC)", water_stressed_area=False,
                   country=country, state=self.states["TN"], city=self.cities["TN", "Hosur"], **facility_defaults)
        self._node(company, "PLT-PNT", "Plant C — Pantnagar", "FACILITY", electricals,
                   facility_type="Manufacturing — electricals", address="Pantnagar, Uttarakhand",
                   grid_region="Uttarakhand (NRLDC)", water_stressed_area=False,
                   country=country, state=self.states["UK"], city=self.cities["UK", "Pantnagar"], **facility_defaults)
        self._node(company, "WH-BHW", "Warehouse — Bhiwandi", "FACILITY", root,
                   facility_type="Distribution warehouse", address="Bhiwandi, Maharashtra",
                   grid_region="Maharashtra (WRLDC)", water_stressed_area=False,
                   country=country, state=self.states["MH"], city=self.cities["MH", "Bhiwandi"], **facility_defaults)

    def _departments(self, company):
        for code, name in (
            ("HR", "Human Resources"), ("FIN", "Finance"), ("EHS", "Environment, Health & Safety"),
            ("OPS", "Operations"), ("LEGAL", "Legal & Compliance"), ("SUS", "Sustainability"),
            ("PROC", "Procurement"),
        ):
            Department.objects.update_or_create(company=company, code=code, defaults={"name": name, "is_active": True})

    def _periods(self):
        # ReportingPeriod rejects overlapping annual periods. Resolve a year
        # by its fiscal boundaries rather than only its display name, so this
        # demo seed remains safe in a database where a user has already
        # created the same April–March period with a different name.
        baseline = self._annual_period(
            "FY 2024-25", date(2024, 4, 1), date(2025, 3, 31), Status.CLOSED, True
        )
        current = self._annual_period(
            "FY 2025-26", date(2025, 4, 1), date(2026, 3, 31), Status.OPEN, False
        )
        # The documented demo state contains Apr–Oct only; avoid generating
        # future children merely for convenience.
        for month, start, end, status in (
            ("Apr 2025", date(2025, 4, 1), date(2025, 4, 30), Status.LOCKED),
            ("May 2025", date(2025, 5, 1), date(2025, 5, 31), Status.LOCKED),
            ("Jun 2025", date(2025, 6, 1), date(2025, 6, 30), Status.LOCKED),
            ("Jul 2025", date(2025, 7, 1), date(2025, 7, 31), Status.LOCKED),
            ("Aug 2025", date(2025, 8, 1), date(2025, 8, 31), Status.LOCKED),
            ("Sep 2025", date(2025, 9, 1), date(2025, 9, 30), Status.LOCKED),
            ("Oct 2025", date(2025, 10, 1), date(2025, 10, 31), Status.OPEN),
        ):
            ReportingPeriod.objects.get_or_create(parent=current, name=month, defaults={"period_type": PeriodType.MONTHLY, "start_date": start, "end_date": end, "status": status})

    @staticmethod
    def _annual_period(name, start_date, end_date, status, is_baseline_year):
        existing = ReportingPeriod.objects.filter(
            parent__isnull=True,
            period_type=PeriodType.ANNUAL,
            start_date=start_date,
            end_date=end_date,
        ).first()
        if existing:
            return existing
        return ReportingPeriod.objects.create(
            name=name,
            period_type=PeriodType.ANNUAL,
            start_date=start_date,
            end_date=end_date,
            status=status,
            is_baseline_year=is_baseline_year,
        )
