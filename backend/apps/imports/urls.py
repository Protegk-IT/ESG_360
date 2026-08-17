from django.urls import path

from .views import (
    ImportBatchDetailAPIView,
    ImportBatchRowsAPIView,
    ImportBatchUploadAPIView,
    ImportBatchValidateAPIView,
    ImportBatchCommitAPIView,
)


urlpatterns = [
    path(
        "batches/",
        ImportBatchUploadAPIView.as_view(),
        name="import-batch-upload",
    ),
    path(
        "batches/<uuid:id>/",
        ImportBatchDetailAPIView.as_view(),
        name="import-batch-detail",
    ),
    path(
        "batches/<uuid:batch_id>/rows/",
        ImportBatchRowsAPIView.as_view(),
        name="import-batch-rows",
    ),
    path(
        "batches/<uuid:id>/validate/",
        ImportBatchValidateAPIView.as_view(),
        name="import-batch-validate",
    ),
    path(
        "batches/<uuid:id>/commit/",
        ImportBatchCommitAPIView.as_view(),
        name="import-batch-commit",
    ),
]