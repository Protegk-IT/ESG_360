from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.permissions import IsAdminUser

from apps.accounts.viewsets import RBACModelViewSet
from .models import ReportingPeriod, Status, PeriodType
from .serializers import ReportingPeriodSerializer
from rest_framework.decorators import action
from django.core.exceptions import ValidationError
from rest_framework import status
from .services import generate_subperiods
from rest_framework import serializers


class GenerateSubperiodsSerializer(serializers.Serializer):
    period_type = serializers.ChoiceField(choices=[
        (PeriodType.MONTHLY, PeriodType.MONTHLY),
        (PeriodType.QUARTERLY, PeriodType.QUARTERLY),
        (PeriodType.HALF_YEARLY, PeriodType.HALF_YEARLY),
    ])


class ReportingPeriodViewSet(RBACModelViewSet):
    module_code = "reporting_period"
    queryset = ReportingPeriod.objects.select_related(
        "parent",
        "locked_by",
    )

    serializer_class = ReportingPeriodSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "period_type",
        "status",
    ]

    search_fields = [
        "name",
    ]

    ordering_fields = [
        "start_date",
        "end_date",
        "name",
    ]

    ordering = [
        "start_date",
    ]

    def get_required_permission(self):
        # Map custom actions to permissions
        if self.action == "current":
            return f"{self.module_code}.view"
        if self.action in ("lock", "unlock"):
            return f"{self.module_code}.edit"
        if self.action == "generate_subperiods":
            return f"{self.module_code}.create"
        return super().get_required_permission()

    @action(detail = False, methods=['get'])
    def current(self, request):
        today = timezone.now().date()
        period = ReportingPeriod.objects.filter(status=Status.OPEN,
            start_date__lte=today,
            end_date__gte=today,
        ).first()

        if not period:
            return Response({'detail': 'No current open reporting period found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(period)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        period = self.get_object()

        if period.status == Status.CLOSED:
            return Response({"detail": "CLOSED periods cannot be locked."}, status=status.HTTP_400_BAD_REQUEST)

        # idempotent: if already locked, return current state
        if period.status == Status.LOCKED:
            serializer = self.get_serializer(period)
            return Response(serializer.data)

        period.status = Status.LOCKED
        period.locked_at = timezone.now()
        period.locked_by = request.user
        period.save()

        serializer = self.get_serializer(period)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
    )
    def unlock(self, request, pk=None):
        period = self.get_object()

        # CLOSED is terminal and cannot be reopened
        if period.status == Status.CLOSED:
            return Response({"detail": "CLOSED periods cannot be unlocked."}, status=status.HTTP_400_BAD_REQUEST)

        # idempotent: if already open, return current state
        if period.status == Status.OPEN:
            serializer = self.get_serializer(period)
            return Response(serializer.data)

        period.status = Status.OPEN
        period.locked_at = None
        period.locked_by = None
        period.save()

        serializer = self.get_serializer(period)
        return Response(serializer.data)
    

    @action(detail=True, methods=["post"], url_path="generate-subperiods")
    def generate_subperiods(self, request, pk=None):

        period = self.get_object()

        serializer = GenerateSubperiodsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period_type = serializer.validated_data["period_type"]

        try:
            # service runs in a transaction and uses select_for_update
            generate_subperiods(period, period_type)

        except ValidationError as exc:
            # ValidationError may contain a dict or list of messages
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages if hasattr(exc, "messages") else str(exc)
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Sub-periods generated successfully."},
            status=status.HTTP_201_CREATED,
        )
