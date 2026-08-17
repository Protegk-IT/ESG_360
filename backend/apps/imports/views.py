from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import ImportBatch
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

        try:
            batch = ImportUploadService.create_batch(
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                import_type=import_type,
                module_code=module_code,
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

        serializer = ImportBatchSerializer(batch)
        return Response(serializer.data)


class ImportBatchRowsAPIView(APIView):
    """
    Return all rows belonging to an import batch.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, batch_id):
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

        rows = batch.rows.order_by(
            "row_number"
        )

        serializer = ImportRowSerializer(
            rows,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
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