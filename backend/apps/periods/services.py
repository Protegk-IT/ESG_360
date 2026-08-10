from calendar import monthrange
from datetime import date

from django.core.exceptions import ValidationError

from .models import PeriodType, ReportingPeriod, Status


def generate_subperiods(parent_period, period_type):
    """
    Generate child reporting periods for the given parent period.
    """

    # Only annual periods can generate sub-periods
    if parent_period.period_type != PeriodType.ANNUAL:
        raise ValidationError("Sub-periods can only be generated for ANNUAL periods.")

    # Prevent duplicate generation
    if parent_period.children.exists():
        raise ValidationError("Sub-periods have already been generated.")

    if period_type == PeriodType.MONTHLY:
        generate_monthly(parent_period)

    elif period_type == PeriodType.QUARTERLY:
        generate_quarterly(parent_period)

    elif period_type == PeriodType.HALF_YEARLY:
        generate_half_yearly(parent_period)

    else:
        raise ValidationError("Invalid period type.")
    

def generate_monthly(parent_period):
    """
    Generate 12 monthly reporting periods.
    """

    current = parent_period.start_date

    while current <= parent_period.end_date:

        last_day = monthrange(current.year, current.month)[1]

        month_end = date(
            current.year,
            current.month,
            last_day,
        )

        if month_end > parent_period.end_date:
            month_end = parent_period.end_date

        ReportingPeriod.objects.create(
            parent=parent_period,
            name=current.strftime("%b %Y"),
            period_type=PeriodType.MONTHLY,
            start_date=current,
            end_date=month_end,
            status=Status.OPEN,
        )

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

def generate_quarterly(parent_period):
    """
    Generate four quarterly reporting periods.
    """

    quarter_start = parent_period.start_date

    for quarter in range(1, 5):

        month = quarter_start.month + 2
        year = quarter_start.year

        if month > 12:
            month -= 12
            year += 1

        last_day = monthrange(year, month)[1]

        quarter_end = date(
            year,
            month,
            last_day,
        )

        if quarter_end > parent_period.end_date:
            quarter_end = parent_period.end_date

        ReportingPeriod.objects.create(
            parent=parent_period,
            name=f"Q{quarter}",
            period_type=PeriodType.QUARTERLY,
            start_date=quarter_start,
            end_date=quarter_end,
            status=Status.OPEN,
        )

        if month == 12:
            quarter_start = date(year + 1, 1, 1)
        else:
            quarter_start = date(year, month + 1, 1)


def generate_half_yearly(parent_period):
    """
    Generate two half-year reporting periods.
    """

    half_start = parent_period.start_date

    for half in range(1, 3):

        month = half_start.month + 5
        year = half_start.year

        if month > 12:
            month -= 12
            year += 1

        last_day = monthrange(year, month)[1]

        half_end = date(
            year,
            month,
            last_day,
        )

        if half_end > parent_period.end_date:
            half_end = parent_period.end_date

        ReportingPeriod.objects.create(
            parent=parent_period,
            name=f"H{half}",
            period_type=PeriodType.HALF_YEARLY,
            start_date=half_start,
            end_date=half_end,
            status=Status.OPEN,
        )

        if month == 12:
            half_start = date(year + 1, 1, 1)
        else:
            half_start = date(year, month + 1, 1)


