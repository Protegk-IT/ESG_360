from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import PeriodType, ReportingPeriod, Status
from .services import generate_subperiods


class ReportingPeriodGenerationTests(TestCase):
    def test_open_annual_period_generates_twelve_months_once(self):
        annual = ReportingPeriod.objects.create(
            name="FY 2026", period_type=PeriodType.ANNUAL,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )

        generate_subperiods(annual, PeriodType.MONTHLY)
        self.assertEqual(annual.children.count(), 12)

        with self.assertRaises(ValidationError):
            generate_subperiods(annual, PeriodType.MONTHLY)

    def test_locked_period_cannot_generate_subperiods(self):
        annual = ReportingPeriod.objects.create(
            name="FY 2027", period_type=PeriodType.ANNUAL,
            start_date=date(2027, 1, 1), end_date=date(2027, 12, 31),
            status=Status.LOCKED,
        )

        with self.assertRaises(ValidationError):
            generate_subperiods(annual, PeriodType.MONTHLY)

    def test_april_to_march_financial_year_generates_correct_boundaries(self):
        annual = ReportingPeriod.objects.create(
            name="FY 2026-27", period_type=PeriodType.ANNUAL,
            start_date=date(2026, 4, 1), end_date=date(2027, 3, 31),
        )

        generate_subperiods(annual, PeriodType.QUARTERLY)
        quarters = list(annual.children.order_by("start_date"))
        self.assertEqual(
            [(period.name, period.start_date, period.end_date) for period in quarters],
            [
                ("Q1", date(2026, 4, 1), date(2026, 6, 30)),
                ("Q2", date(2026, 7, 1), date(2026, 9, 30)),
                ("Q3", date(2026, 10, 1), date(2026, 12, 31)),
                ("Q4", date(2027, 1, 1), date(2027, 3, 31)),
            ],
        )

        second_annual = ReportingPeriod.objects.create(
            name="FY 2027-28", period_type=PeriodType.ANNUAL,
            start_date=date(2027, 4, 1), end_date=date(2028, 3, 31),
        )
        generate_subperiods(second_annual, PeriodType.HALF_YEARLY)
        self.assertEqual(
            list(second_annual.children.order_by("start_date").values_list("start_date", "end_date")),
            [(date(2027, 4, 1), date(2027, 9, 30)), (date(2027, 10, 1), date(2028, 3, 31))],
        )
