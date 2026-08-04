from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAdminUser

from .models import ReportingPeriod, Status
from .serializers import ReportingPeriodSerializer
from rest_framework.decorators import action


class ReportingPeriodViewSet(viewsets.ModelViewSet):
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

    @action(detail = False, methods=['get'])
    def current(self, request):
        today = timezone.now().date()
        period = ReportingPeriod.objects.filter(status=Status.OPEN,
            start_date__lte=today,
            end_date__gte=today,
        ).first()

        if not period:
            return Response({'detail': 'No current open reporting period found.'}, status=404)
        serializer = self.get_serializer(period)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        period = self.get_object()

        period.status = Status.LOCKED
        period.locked_at = timezone.now()
        period.locked_by = request.user
        period.save()

        serializer = self.get_serializer(period)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdminUser], #swap this empty list with admin permission class
    )
    def unlock(self, request, pk=None):
        period = self.get_object()

        period.status = Status.OPEN
        period.locked_at = None
        period.locked_by = None
        period.save()

        serializer = self.get_serializer(period)
        return Response(serializer.data)
    

    @action(detail=True, methods=["post"])
    def generate_subperiods(self, request, pk=None):

        period = self.get_object()

        period_type = request.data.get("period_type")

        try:
            generate_subperiods(period, period_type)

        except ValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Sub-periods generated successfully."},
            status=status.HTTP_201_CREATED,
        )

