from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRolePermission
from apps.accounts.viewsets import RBACModelViewSet

from .models import (
    ReportRun,
    FrameworkSnapshot,
)
from .serializers import (
    ReportRunSerializer,
    ReportRunDetailSerializer,
    FrameworkSnapshotSerializer,
)
from .services import freeze_report_run


# ============================================================
# M8 REPORTING RBAC BASE
# ============================================================

class ReportingModelViewSet(RBACModelViewSet):
    """
    Base ViewSet for M8 reporting APIs.

    Authentication and RBAC are delegated to the centralized
    RBACModelViewSet / HasRolePermission implementation.

    The permission code used here must be an existing canonical
    permission from the platform permission catalog.
    """

    permission_code = "report.create_run"

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]

        return super().get_permissions()


# ============================================================
# REPORT RUN
# ============================================================

class ReportRunViewSet(ReportingModelViewSet):
    """
    ReportRun CRUD API.

    GET /report-runs/
        List report runs.

    POST /report-runs/
        Create a report run.

    GET /report-runs/{id}/
        Retrieve a report run.

    PATCH /report-runs/{id}/
        Modify an unfrozen report run.

    DELETE /report-runs/{id}/
        Delete an unfrozen report run.

    A frozen report run cannot be modified or deleted.
    """

    serializer_class = ReportRunSerializer

    queryset = (
        ReportRun.objects
        .select_related(
            "reporting_period",
            "framework_version",
            "framework_version__framework",
            "created_by",
        )
        .order_by("-created_at")
    )

    def get_queryset(self):
        """
        Return ReportRun records using efficient related-object
        loading and optional filtering.

        Supported query parameters:

            ?reporting_period=<uuid>
            ?framework_version=<uuid>
            ?status=<status>
        """

        queryset = (
            ReportRun.objects
            .select_related(
                "reporting_period",
                "framework_version",
                "framework_version__framework",
                "created_by",
            )
            .order_by("-created_at")
        )

        reporting_period = self.request.query_params.get(
            "reporting_period"
        )

        framework_version = self.request.query_params.get(
            "framework_version"
        )

        status_value = self.request.query_params.get(
            "status"
        )

        if reporting_period:
            queryset = queryset.filter(
                reporting_period_id=reporting_period
            )

        if framework_version:
            queryset = queryset.filter(
                framework_version_id=framework_version
            )

        if status_value:
            queryset = queryset.filter(
                status=status_value
            )

        return queryset

    def get_serializer_class(self):
        """
        Use the detailed serializer for retrieve.

        List/create continue using the normal ReportRun serializer.
        """

        if self.action == "retrieve":
            return ReportRunDetailSerializer

        return ReportRunSerializer

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):
        """
        Prevent modification of a frozen report run.
        """

        instance = self.get_object()

        if instance.is_frozen:
            return Response(
                {
                    "detail": (
                        "A frozen report run cannot be modified."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(
            request,
            *args,
            **kwargs,
        )

    def partial_update(
        self,
        request,
        *args,
        **kwargs,
    ):
        """
        Prevent partial modification of a frozen report run.
        """

        instance = self.get_object()

        if instance.is_frozen:
            return Response(
                {
                    "detail": (
                        "A frozen report run cannot be modified."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().partial_update(
            request,
            *args,
            **kwargs,
        )

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):
        """
        Prevent deletion of a frozen historical report run.
        """

        instance = self.get_object()

        if instance.is_frozen:
            return Response(
                {
                    "detail": (
                        "A frozen report run cannot be deleted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )


# ============================================================
# FREEZE REPORT RUN
# ============================================================

class ReportRunFreezeView(APIView):
    """
    Freeze the framework structure for one ReportRun.

    POST /report-runs/{id}/freeze/

    This is the ONLY API operation responsible for creating
    the M8 framework snapshot.

    The actual business operation is delegated to:

        freeze_report_run()

    in services.py.

    The service owns the transaction and snapshot creation.

    This view only handles HTTP concerns and converts domain
    validation errors into proper DRF responses.
    """

    permission_classes = (
        IsAuthenticated,
        HasRolePermission,
    )

    # IMPORTANT:
    #
    # This must be an existing canonical permission from the
    # central RBAC permission catalog.
    #
    # Do not create a new permission such as:
    #
    #     report_run.freeze
    #
    # unless the platform RBAC contract explicitly requires it.

    permission_code = "report.create_run"

    def post(self, request, run_id):
        """
        Execute the controlled freeze operation.
        """

        report_run = get_object_or_404(
            ReportRun.objects.select_related(
                "reporting_period",
                "framework_version",
                "framework_version__framework",
                "created_by",
            ),
            pk=run_id,
        )

        try:
            report_run = freeze_report_run(
                report_run
            )

        except DjangoValidationError as exc:
            """
            The domain service uses Django's ValidationError
            for business-rule violations.

            Convert it into DRF's normal HTTP 400 response
            instead of allowing Django DEBUG to display a
            server traceback.
            """

            messages = getattr(
                exc,
                "messages",
                [str(exc)],
            )

            return Response(
                {
                    "detail": messages,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReportRunDetailSerializer(
            report_run,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# FROZEN REPORT STRUCTURE
# ============================================================

class ReportRunSnapshotView(APIView):
    """
    Retrieve the immutable framework snapshot for a ReportRun.

    GET /report-runs/{id}/snapshot/

    Read access requires authentication only.

    The snapshot cannot be created or modified through this
    endpoint.
    """

    permission_classes = (
        IsAuthenticated,
    )

    def get(self, request, run_id):
        """
        Return the frozen framework structure.
        """

        report_run = get_object_or_404(
            ReportRun.objects.select_related(
                "framework_snapshot",
            ),
            pk=run_id,
        )

        # A snapshot is meaningful only after the report run
        # has been successfully frozen.
        if not report_run.is_frozen:
            return Response(
                {
                    "detail": (
                        "The report run has not been frozen yet."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # IMPORTANT:
        #
        # report_run.framework_snapshot is already a
        # FrameworkSnapshot model instance.
        #
        # Therefore DO NOT do:
        #
        #     get_object_or_404(
        #         report_run.framework_snapshot
        #     )
        #
        # get_object_or_404() expects a Model class,
        # Manager, or QuerySet — not an existing instance.

        try:
            snapshot = report_run.framework_snapshot

        except FrameworkSnapshot.DoesNotExist:
            # This represents an inconsistent database state:
            # the ReportRun says it is frozen, but its snapshot
            # does not exist.
            return Response(
                {
                    "detail": (
                        "The report run is marked as frozen "
                        "but its framework snapshot does not exist."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = FrameworkSnapshotSerializer(
            snapshot,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )