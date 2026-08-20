from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import OrgNode
from apps.periods.models import ReportingPeriod

from .models import ImportBatch, ImportRow
from .parser import ImportFileError
from .serializers import (
    ImportBatchSerializer,
    ImportRowSerializer,
)
from .services import (
    ImportBatchService,
    ImportUploadService,
)


class ImportBatchUploadAPIView(APIView):
    """
    Upload an Excel file and create an ImportBatch.

    The uploaded file is stored using Django's configured
    storage backend before it is parsed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {
                    "file": [
                        "An Excel file is required."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        import_type = request.data.get(
            "import_type"
        )

        if import_type not in ImportBatch.ImportType.values:
            return Response(
                {
                    "import_type": [
                        "Invalid import type."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        module_code = request.data.get(
            "module_code"
        )

        org_node_id = request.data.get(
            "org_node"
        )

        reporting_period_id = request.data.get(
            "reporting_period"
        )

        org_node = None

        if org_node_id:
            org_node = get_object_or_404(
                OrgNode,
                pk=org_node_id,
            )

        reporting_period = None

        if reporting_period_id:
            reporting_period = get_object_or_404(
                ReportingPeriod,
                pk=reporting_period_id,
            )

        try:
            batch = ImportUploadService.create_batch(
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                import_type=import_type,
                module_code=module_code,
                org_node=org_node,
                reporting_period=reporting_period,
            )

            serializer = ImportBatchSerializer(
                batch
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except ImportFileError as exc:
            return Response(
                {
                    "file": [
                        str(exc)
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except DjangoValidationError as exc:
            return Response(
                (
                    exc.message_dict
                    if hasattr(
                        exc,
                        "message_dict",
                    )
                    else {
                        "detail": exc.messages
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )


class ImportBatchDetailAPIView(APIView):
    """
    Return details of an import batch.

    Normal users can only inspect batches they uploaded.
    Superusers can inspect any batch.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        if request.user.is_superuser:
            batch = get_object_or_404(
                ImportBatch,
                pk=id,
            )
        else:
            batch = get_object_or_404(
                ImportBatch,
                pk=id,
                uploaded_by=request.user,
            )

        serializer = ImportBatchSerializer(
            batch
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class ImportRowPagination(PageNumberPagination):
    """
    Pagination for import batch rows.

    Default:
        20 rows per page.

    Client can request:
        ?page=2
        ?page_size=50

    Maximum:
        100 rows per page.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ImportBatchRowsAPIView(APIView):
    """
    Return paginated rows belonging to an import batch.

    Supported query parameters:

        ?page=1
        ?page_size=20
        ?status=VALID
        ?status=ERROR
        ?status=SKIPPED
        ?status=COMMITTED

    Examples:

        /api/imports/batches/<id>/rows/

        /api/imports/batches/<id>/rows/?page=2

        /api/imports/batches/<id>/rows/?status=ERROR

        /api/imports/batches/<id>/rows/?status=ERROR&page_size=50
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, batch_id):
        # ------------------------------------------------------------
        # Get batch with the same authorization rules as before.
        # ------------------------------------------------------------

        if request.user.is_superuser:
            batch = ImportBatch.objects.filter(
                id=batch_id
            ).first()
        else:
            batch = ImportBatch.objects.filter(
                id=batch_id,
                uploaded_by=request.user,
            ).first()

        if batch is None:
            return Response(
                {
                    "detail": "Import batch not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ------------------------------------------------------------
        # Start with all rows belonging to this batch.
        # ------------------------------------------------------------

        rows = batch.rows.all()

        # ------------------------------------------------------------
        # Optional status filtering.
        #
        # Example:
        # ?status=ERROR
        # ------------------------------------------------------------

        row_status = request.query_params.get(
            "status"
        )

        if row_status:
            valid_statuses = {
                value
                for value, _ in ImportRow.Status.choices
            }

            if row_status not in valid_statuses:
                return Response(
                    {
                        "status": [
                            (
                                "Invalid status. "
                                f"Allowed values are: "
                                f"{', '.join(sorted(valid_statuses))}."
                            )
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            rows = rows.filter(
                status=row_status
            )

        # ------------------------------------------------------------
        # Always return rows in spreadsheet row-number order.
        # ------------------------------------------------------------

        rows = rows.order_by(
            "row_number"
        )

        # ------------------------------------------------------------
        # Apply pagination.
        # ------------------------------------------------------------

        paginator = ImportRowPagination()

        paginated_rows = paginator.paginate_queryset(
            rows,
            request,
            view=self,
        )

        serializer = ImportRowSerializer(
            paginated_rows,
            many=True,
        )

        return paginator.get_paginated_response(
            serializer.data
        )


class ImportBatchValidateAPIView(APIView):
    """
    Validate all rows in an import batch.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        if request.user.is_superuser:
            batch = ImportBatch.objects.filter(
                id=id
            ).first()
        else:
            batch = ImportBatch.objects.filter(
                id=id,
                uploaded_by=request.user,
            ).first()

        if batch is None:
            return Response(
                {
                    "detail": "Import batch not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            batch = ImportBatchService.validate_batch(
                batch
            )

        except DjangoValidationError as exc:
            if hasattr(
                exc,
                "message_dict",
            ):
                data = exc.message_dict
            else:
                data = {
                    "detail": exc.messages
                }

            return Response(
                data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ImportBatchSerializer(
            batch
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class ImportBatchCommitAPIView(APIView):
    """
    Commit a validated import batch.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        if request.user.is_superuser:
            batch = ImportBatch.objects.filter(
                id=id
            ).first()
        else:
            batch = ImportBatch.objects.filter(
                id=id,
                uploaded_by=request.user,
            ).first()

        if batch is None:
            return Response(
                {
                    "detail": "Import batch not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            batch = ImportBatchService.commit(
                batch
            )

        except DjangoValidationError as exc:
            if hasattr(
                exc,
                "message_dict",
            ):
                data = exc.message_dict
            else:
                data = {
                    "detail": exc.messages
                }

            return Response(
                data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ImportBatchSerializer(
            batch
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )