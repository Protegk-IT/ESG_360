from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404

from apps.accounts.permissions import HasRolePermission
from apps.accounts.services.rbac import RBACService
from apps.accounts.viewsets import RBACModelViewSet

from apps.data_capture.models import Answer

from .models import (
    CalculationResult,
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)

from .serializers import (
    ApprovedAnswerCalculationRequestSerializer,
    CalculationPreviewSerializer,
    CalculationResultSerializer,
    CalculationRuleSerializer,
    EmissionFactorSerializer,
    EmissionFactorSourceSerializer,
)
from .services.approved_answer import ApprovedAnswerCalculationService, CalculationResultService


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

        try:
            result = serializer.calculate()
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(
                    exc.message_dict
                )

            raise serializers.ValidationError(
                {
                    "calculation": exc.messages,
                }
            )

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


def get_scoped_answer_or_404(answer_id, user):
    try:
        answer = Answer.objects.select_related(
            "submission",
            "submission__data_request",
            "submission__data_request__org_node",
            "submission__data_request__reporting_period",
            "submission__data_request__datapoint",
            "unit",
        ).get(pk=answer_id)
    except Answer.DoesNotExist:
        raise Http404

    if user.is_superuser:
        return answer

    org_node_id = answer.submission.data_request.org_node_id

    allowed_nodes = RBACService.get_allowed_org_nodes(
        user,
        "data.approve",
        module_code="data",
    )

    if allowed_nodes is not None and org_node_id not in allowed_nodes:
        raise Http404

    return answer

class ApprovedAnswerCalculationAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    permission_code = "data.approve"

    def get_required_permission(self):
        return "data.approve"

    def post(self, request, *args, **kwargs):
        request_serializer = ApprovedAnswerCalculationRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        answer_id = request_serializer.validated_data["answer"]
        calculation_date = request_serializer.validated_data["calculation_date"]
        geography = request_serializer.validated_data.get("geography")

        answer = get_scoped_answer_or_404(
            answer_id,
            request.user,
        )
        try:
            calculation = ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=calculation_date,
                geography=geography or None,
                actor=request.user,
            )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict)
            raise serializers.ValidationError({"calculation": exc.messages})

        return Response(
            {
                "answer": str(answer.id),
                "activity_key": calculation["activity_key"],
                "calculation_date": calculation["calculation_date"].isoformat(),
                "geography": calculation.get("geography") or "",
                "input_quantity": str(calculation["input_quantity"]),
                "input_unit": calculation["input_unit"].id,
                "normalized_quantity": str(calculation["normalized_quantity"]),
                "calculated_value": str(calculation["calculated_value"]),
                "output_unit": calculation["output_unit"].id,
                "factor": calculation["factor"].id,
                "calculation_rule": calculation["calculation_rule"].id,
            },
            status=status.HTTP_200_OK,
        )


class CalculationResultViewSet(RBACModelViewSet):
    serializer_class = CalculationResultSerializer
    permission_code = "data.approve"
    module_code = "data"
    scope_field = "org_node"
    scope_permission = "data.approve"

    queryset = CalculationResult.objects.select_related(
        "answer",
        "submission",
        "data_request",
        "datapoint",
        "org_node",
        "reporting_period",
        "calculation_rule",
        "emission_factor",
        "emission_factor__source",
        "input_unit",
        "output_unit",
        "calculated_by",
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_superuser:
            return queryset

        allowed_nodes = RBACService.get_allowed_org_nodes(
            self.request.user,
            "data.approve",
            module_code="data",
        )

        if allowed_nodes is None:
            return queryset

        if not allowed_nodes:
            return queryset.none()

        return queryset.filter(
            org_node_id__in=allowed_nodes
        )

    def get_permissions(self):
        return [IsAuthenticated(), HasRolePermission()]

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    "Calculation results must be created through "
                    "the calculation result creation endpoint."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "Calculation results are immutable."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "Calculation results are immutable."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "Calculation results cannot be deleted."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
    

class CalculationResultCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    permission_code = "data.approve"

    def get_required_permission(self):
        return "data.approve"

    def post(self, request, *args, **kwargs):
        request_serializer = ApprovedAnswerCalculationRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        answer_id = request_serializer.validated_data["answer"]
        calculation_date = request_serializer.validated_data["calculation_date"]
        geography = request_serializer.validated_data.get("geography")

        answer = get_scoped_answer_or_404(
            answer_id,
            request.user,
        )
        try:
            calculation = ApprovedAnswerCalculationService.calculate(
                answer=answer,
                calculation_date=calculation_date,
                geography=geography or None,
                actor=request.user,
            )
            result = CalculationResultService.persist(calculation=calculation, actor=request.user)
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict)
            raise serializers.ValidationError({"calculation": exc.messages})

        serializer = CalculationResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)