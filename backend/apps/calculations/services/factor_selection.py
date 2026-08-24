from datetime import date

from django.core.exceptions import ValidationError

from apps.calculations.models import EmissionFactor
from django.db.models import Q


class FactorSelectionService:
    """
    Select exactly one valid emission factor based on explicit
    calculation context.

    Selection considers:
    - activity key
    - optional date
    - optional geography
    - active state
    """

    @staticmethod
    def select_factor(
        *,
        activity_key: str,
        calculation_date: date | None = None,
        geography: str | None = None,
    ) -> EmissionFactor:

        queryset = EmissionFactor.objects.filter(
            activity_key=activity_key,
            is_active=True,
            source__is_active=True
        )

        # -------------------------------------------------
        # DATE VALIDITY
        # -------------------------------------------------

        if calculation_date is not None:
            queryset = queryset.filter(
                #factor effective
                Q(effective_from__isnull=True)
                |Q(effective_from__lte=calculation_date),
                Q(effective_to__isnull=True)
                |Q(effective_to__gte=calculation_date),

                #source effective range
                Q(source__effective_from__isnull=True)
                | Q(source__effective_from__lte=calculation_date),
                Q(source__effective_to__isnull=True)
                | Q(source__effective_to__gte=calculation_date),
            )

        # -------------------------------------------------
        # GEOGRAPHY
        # -------------------------------------------------

        if geography:
            queryset = queryset.filter(geography=geography)

        # -------------------------------------------------
        # SELECTION RESULT
        # -------------------------------------------------

        factors = list(queryset)

        if not factors:
            raise ValidationError(
                {
                    "factor": (
                        "No active emission factor matches "
                        "the supplied calculation context."
                    )
                }
            )

        if len(factors) > 1:
            raise ValidationError(
                {
                    "factor": (
                        "Multiple emission factors match the supplied "
                        "calculation context. Factor selection is ambiguous."
                    )
                }
            )

        return factors[0]