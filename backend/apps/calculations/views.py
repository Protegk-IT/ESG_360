from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRolePermission
from apps.accounts.viewsets import RBACModelViewSet

from .models import (
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)

from .serializers import (
    CalculationPreviewSerializer,
    CalculationRuleSerializer,
    EmissionFactorSerializer,
    EmissionFactorSourceSerializer,
)


class EmissionFactorBaseViewSet(RBACModelViewSet):
    """
    Common ViewSet for M6 emission-factor and calculation
    catalog models.

    Catalog data is readable by authenticated users.

    Administrative changes require:
        emission_factor.manage
    """

    permission_code = "emission_factor.manage"

    def get_permissions(self):
        if self.action in {
            "create",
            "update",
            "partial_update",
            "destroy",
        }:
            return [
                IsAuthenticated(),
                HasRolePermission(),
            ]

        return [
            IsAuthenticated(),
        ]

    def get_required_permission(self):
        return "emission_factor.manage"


class EmissionFactorSourceViewSet(EmissionFactorBaseViewSet):
    """
    API for emission-factor sources / factor sets.

    Sources represent the provenance and version context
    for a group of emission factors.
    """

    queryset = EmissionFactorSource.objects.all()

    serializer_class = EmissionFactorSourceSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "is_active",
        "publisher",
        "version",
    ]

    search_fields = [
        "code",
        "name",
        "publisher",
        "version",
        "source_reference",
    ]

    ordering_fields = [
        "code",
        "name",
        "version",
        "publication_date",
        "effective_from",
        "effective_to",
    ]

    ordering = [
        "code",
        "version",
    ]


class EmissionFactorViewSet(EmissionFactorBaseViewSet):
    """
    API for emission-factor definitions.
    """

    queryset = EmissionFactor.objects.select_related(
        "source",
        "input_unit",
        "output_unit",
    )

    serializer_class = EmissionFactorSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "source",
        "activity_key",
        "geography",
        "input_unit",
        "output_unit",
        "is_active",
    ]

    search_fields = [
        "code",
        "activity_key",
        "geography",
        "notes",
    ]

    ordering_fields = [
        "code",
        "activity_key",
        "factor_value",
        "effective_from",
        "effective_to",
    ]

    ordering = [
        "code",
    ]


class CalculationRuleViewSet(EmissionFactorBaseViewSet):
    """
    API for declarative calculation rules.

    Calculation rules contain metadata/configuration only.
    They must not contain executable Python code or arbitrary
    expressions.
    """

    queryset = CalculationRule.objects.select_related(
        "datapoint",
    )

    serializer_class = CalculationRuleSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "datapoint",
        "is_active",
    ]

    search_fields = [
        "code",
        "name",
        "description",
    ]

    ordering_fields = [
        "code",
        "name",
        "created_at",
    ]

    ordering = [
        "code",
    ]


class CalculationPreviewAPIView(APIView):
    """
    Perform an explicit calculation without persisting
    a calculated result.

    This endpoint does not depend on M5 Answer models.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, *args, **kwargs):
        serializer = CalculationPreviewSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        result = serializer.calculate()

        return Response(
            {
                "input_quantity": str(
                    result["input_quantity"]
                ),
                "input_unit": result["input_unit"].id,
                "normalized_quantity": str(
                    result["normalized_quantity"]
                ),
                "calculated_value": str(
                    result["calculated_value"]
                ),
                "output_unit": result["output_unit"].id,
                "factor": result["factor"].id,
            },
            status=status.HTTP_200_OK,
        )