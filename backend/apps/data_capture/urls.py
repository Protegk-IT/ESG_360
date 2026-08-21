from django.urls import path

from .views import (
    DataRequestDetailAPIView,
    DataRequestListCreateAPIView,
    DataRequestReassignAPIView,
    EvidenceDetailAPIView,
    EvidenceDownloadAPIView,
    EvidenceListUploadAPIView,
    MyDataRequestListAPIView,
    SubmissionAnswerAPIView,
    SubmissionApproveAPIView,
    SubmissionDetailAPIView,
    SubmissionHistoryAPIView,
    SubmissionRejectAPIView,
    SubmissionReopenAPIView,
    SubmissionSubmitAPIView,
    SubmissionTableRowDetailAPIView,
    SubmissionTableRowsAPIView,
)

app_name = "data_capture"

urlpatterns = [
    path("requests/", DataRequestListCreateAPIView.as_view(), name="request-list"),
    path("requests/mine/", MyDataRequestListAPIView.as_view(), name="request-mine"),
    path("requests/<uuid:request_id>/", DataRequestDetailAPIView.as_view(), name="request-detail"),
    path("requests/<uuid:request_id>/reassign/", DataRequestReassignAPIView.as_view(), name="request-reassign"),
    path("requests/<uuid:request_id>/submission/", SubmissionDetailAPIView.as_view(), name="submission-detail"),
    path("requests/<uuid:request_id>/submission/answer/", SubmissionAnswerAPIView.as_view(), name="submission-answer"),
    path("requests/<uuid:request_id>/submission/table-rows/", SubmissionTableRowsAPIView.as_view(), name="submission-table-rows"),
    path("requests/<uuid:request_id>/submission/table-rows/<uuid:row_id>/", SubmissionTableRowDetailAPIView.as_view(), name="submission-table-row-detail"),
    path("requests/<uuid:request_id>/submission/history/", SubmissionHistoryAPIView.as_view(), name="submission-history"),
    path("requests/<uuid:request_id>/evidence/", EvidenceListUploadAPIView.as_view(), name="evidence-list"),
    path("requests/<uuid:request_id>/evidence/<uuid:evidence_id>/", EvidenceDetailAPIView.as_view(), name="evidence-detail"),
    path("requests/<uuid:request_id>/evidence/<uuid:evidence_id>/download/", EvidenceDownloadAPIView.as_view(), name="evidence-download"),
    path("requests/<uuid:request_id>/submission/submit/", SubmissionSubmitAPIView.as_view(), name="submission-submit"),
    path("requests/<uuid:request_id>/submission/approve/", SubmissionApproveAPIView.as_view(), name="submission-approve"),
    path("requests/<uuid:request_id>/submission/reject/", SubmissionRejectAPIView.as_view(), name="submission-reject"),
    path("requests/<uuid:request_id>/submission/reopen/", SubmissionReopenAPIView.as_view(), name="submission-reopen"),
]
