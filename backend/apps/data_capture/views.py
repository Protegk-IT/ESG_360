"""Session-authenticated, scoped API for the M5 domain service."""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.services.rbac import RBACService
from apps.core.response import created_response, success_response

from .authorization import (
    READ_PERMISSIONS,
    has_scoped_permission,
    permission_scoped_request_queryset,
    readable_request_queryset,
)
from .models import AnswerTableRow, CampaignTarget, CollectionCampaign, DataRequest, EvidenceFile
from .pagination import DataCapturePagination
from .serializers import (
    DataRequestCreateSerializer,
    DataRequestEventSerializer,
    DataRequestListSerializer,
    DataRequestSerializer,
    EvidenceFileSerializer,
    EvidenceUploadSerializer,
    ReasonSerializer,
    ReassignSerializer,
    SubmissionEventSerializer,
    SubmissionSerializer,
    TableRowWriteSerializer,
    TypedValueWriteSerializer,
    CampaignBulkReassignSerializer,
    CampaignGenerateSerializer,
    CampaignTargetSerializer,
    CollectionCampaignCreateSerializer,
    CollectionCampaignEventSerializer,
    CollectionCampaignListSerializer,
)
from .services.campaigns import CollectionCampaignService
from .services.lifecycle import DataCaptureLifecycleService
from .services.evidence import EvidenceService


def _domain_error(exc):
    """Translate Django-domain failures into the shared DRF error envelope."""

    if isinstance(exc, DjangoPermissionDenied):
        raise PermissionDenied(str(exc)) from exc
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(detail) from exc


class DataCaptureAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    request_queryset = DataRequest.objects.select_related(
        "datapoint__category", "datapoint__unit_family", "datapoint__default_unit",
        "org_node", "reporting_period", "assignee", "requested_by", "submission",
    ).prefetch_related(
        "submission__answer__table_rows__cells__column",
    )
    list_queryset = DataRequest.objects.select_related(
        "datapoint", "org_node", "reporting_period", "assignee", "submission"
    )

    def paginated_success(self, queryset, serializer_class):
        paginator = DataCapturePagination()
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        return success_response(paginator.payload(serializer_class(page, many=True)))

    def require_permission(self, permission_code):
        if not RBACService.has_permission(self.request.user, permission_code):
            raise PermissionDenied("You don't have permission to perform this action.")

    def readable_queryset(self):
        return readable_request_queryset(self.request_queryset, self.request.user)

    def readable_list_queryset(self):
        return readable_request_queryset(self.list_queryset, self.request.user)

    def get_readable_request(self, request_id):
        return get_object_or_404(self.readable_queryset(), pk=request_id)

    def get_action_request(self, request_id, permission_code, *, require_assignee=False):
        self.require_permission(permission_code)
        queryset = self.request_queryset
        if not self.request.user.is_superuser:
            allowed_nodes = RBACService.get_allowed_org_nodes(
                self.request.user,
                permission_code,
                module_code=permission_code.split(".", 1)[0],
            )
            if allowed_nodes is not None:
                queryset = queryset.filter(org_node_id__in=allowed_nodes)
        if require_assignee:
            queryset = queryset.filter(assignee=self.request.user)
        return get_object_or_404(queryset, pk=request_id)

    def get_permission_scoped_request(self, request_id, permission_code):
        self.require_permission(permission_code)
        queryset = permission_scoped_request_queryset(
            self.request_queryset, self.request.user, permission_code
        )
        return get_object_or_404(queryset, pk=request_id)

    @staticmethod
    def service_call(callable_, *args, **kwargs):
        try:
            return callable_(*args, **kwargs)
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            _domain_error(exc)


class DataRequestListCreateAPIView(DataCaptureAPIView):
    """Scoped M5 request list and `data.manage` request creation."""

    def get(self, request):
        if not any(RBACService.has_permission(request.user, code) for code in READ_PERMISSIONS):
            raise PermissionDenied("You don't have permission to perform this action.")
        queryset = self.readable_list_queryset()
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        return self.paginated_success(queryset, DataRequestListSerializer)

    def post(self, request):
        self.require_permission("data.manage")
        serializer = DataRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if not has_scoped_permission(request.user, "data.manage", values["org_node"].id):
            # Preserve protected-object behavior for an out-of-scope target.
            raise NotFound("Organization node not found.")
        data_request = self.service_call(
            DataCaptureLifecycleService.create_request,
            actor=request.user,
            **values,
        )
        return created_response(DataRequestSerializer(data_request).data, "Data request created.")


class MyDataRequestListAPIView(DataCaptureAPIView):
    def get(self, request):
        if not any(RBACService.has_permission(request.user, code) for code in READ_PERMISSIONS):
            raise PermissionDenied("You don't have permission to perform this action.")
        queryset = self.readable_list_queryset().filter(assignee=request.user)
        return self.paginated_success(queryset, DataRequestListSerializer)


class DataRequestDetailAPIView(DataCaptureAPIView):
    def get(self, request, request_id):
        data_request = self.get_readable_request(request_id)
        return success_response(DataRequestSerializer(data_request).data)


class DataRequestReassignAPIView(DataCaptureAPIView):
    def post(self, request, request_id):
        data_request = self.get_action_request(request_id, "data.manage")
        serializer = ReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = self.service_call(
            DataCaptureLifecycleService.reassign_request,
            data_request,
            actor=request.user,
            **serializer.validated_data,
        )
        return success_response(DataRequestSerializer(updated).data, "Data request reassigned.")


class CollectionCampaignAPIView(DataCaptureAPIView):
    """Campaign transport/authentication; service owns all mutations."""

    campaign_queryset = CollectionCampaign.objects.select_related(
        "company", "reporting_period", "created_by"
    )

    def require_manage(self):
        self.require_permission("data.manage")

    def visible_campaign_queryset(self):
        """Campaign metadata is visible only through its manager scope.

        An empty draft remains visible to its creator.  Once targets exist, a
        manager only sees campaigns containing targets in their own qualifying
        ``data.manage`` scope; detail/progress subsequently scope target rows.
        """

        self.require_manage()
        if self.request.user.is_superuser:
            return self.campaign_queryset
        allowed_nodes = RBACService.get_allowed_org_nodes(
            self.request.user, "data.manage", module_code="data"
        )
        if allowed_nodes is None:
            return self.campaign_queryset
        return self.campaign_queryset.filter(
            Q(created_by=self.request.user, targets__isnull=True) |
            Q(targets__org_node_id__in=allowed_nodes)
        ).distinct()

    def scoped_targets(self, campaign):
        queryset = CampaignTarget.objects.filter(campaign=campaign).select_related(
            "datapoint", "org_node", "assignee", "data_request__submission"
        )
        if self.request.user.is_superuser:
            return queryset
        allowed_nodes = RBACService.get_allowed_org_nodes(
            self.request.user, "data.manage", module_code="data"
        )
        if allowed_nodes is None:
            return queryset
        return queryset.filter(org_node_id__in=allowed_nodes)

    def get_campaign(self, campaign_id):
        return get_object_or_404(self.visible_campaign_queryset(), pk=campaign_id)

    def campaign_payload(self, campaign):
        payload = CollectionCampaignListSerializer(campaign).data
        targets = self.scoped_targets(campaign)
        payload["default_instructions"] = campaign.default_instructions
        payload["targets"] = CampaignTargetSerializer(targets, many=True).data
        # Generation/reassignment summaries are campaign-wide aggregates. Do
        # not disclose them to a manager who only covers a subset of targets.
        events = campaign.events.select_related("actor") if self.fully_manageable(campaign) else []
        payload["events"] = CollectionCampaignEventSerializer(events, many=True).data
        return payload

    def fully_manageable(self, campaign):
        """Actions affecting all campaign state need coverage of every target."""

        total = campaign.targets.count()
        return total == self.scoped_targets(campaign).count()


class CollectionCampaignListCreateAPIView(CollectionCampaignAPIView):
    def get(self, request):
        return self.paginated_success(
            self.visible_campaign_queryset(), CollectionCampaignListSerializer
        )

    def post(self, request):
        self.require_manage()
        serializer = CollectionCampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = self.service_call(
            CollectionCampaignService.create_campaign,
            actor=request.user,
            **serializer.validated_data,
        )
        return created_response(self.campaign_payload(campaign), "Collection campaign created.")


class CollectionCampaignDetailAPIView(CollectionCampaignAPIView):
    def get(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)
        return success_response(self.campaign_payload(campaign))


class CollectionCampaignTargetListAPIView(CollectionCampaignAPIView):
    def get(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)
        return self.paginated_success(self.scoped_targets(campaign), CampaignTargetSerializer)


class CollectionCampaignGenerateAPIView(CollectionCampaignAPIView):
    def post(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)
        serializer = CampaignGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Keep protected-object behavior for a guessed/out-of-scope target.
        # The service repeats this authorization defensively for non-HTTP use.
        if any(
            not has_scoped_permission(request.user, "data.manage", target["org_node"].id)
            for target in serializer.validated_data["targets"]
        ):
            raise NotFound("Organization node not found.")
        targets, summary = self.service_call(
            CollectionCampaignService.generate_requests,
            campaign,
            actor=request.user,
            targets=serializer.validated_data["targets"],
        )
        return success_response(
            {"summary": summary, "targets": CampaignTargetSerializer(targets, many=True).data},
            "Collection campaign generation completed.",
        )


class CollectionCampaignProgressAPIView(CollectionCampaignAPIView):
    def get(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)
        return success_response(CollectionCampaignService.progress(self.scoped_targets(campaign)))


class CollectionCampaignBulkReassignAPIView(CollectionCampaignAPIView):
    def post(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)
        serializer = CampaignBulkReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scoped_ids = set(
            self.scoped_targets(campaign).filter(
                id__in=serializer.validated_data["target_ids"]
            ).values_list("id", flat=True)
        )
        if scoped_ids != set(serializer.validated_data["target_ids"]):
            raise NotFound("Collection campaign target not found.")
        targets = self.service_call(
            CollectionCampaignService.bulk_reassign,
            campaign,
            actor=request.user,
            target_ids=serializer.validated_data["target_ids"],
            assignee=serializer.validated_data["assignee"],
            reason=serializer.validated_data["reason"],
        )
        return success_response(
            CampaignTargetSerializer(targets, many=True).data,
            "Campaign requests reassigned.",
        )


class CollectionCampaignCloseAPIView(CollectionCampaignAPIView):
    def post(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)
        if not self.fully_manageable(campaign):
            raise NotFound("Collection campaign not found.")
        campaign = self.service_call(
            CollectionCampaignService.close_campaign, campaign, actor=request.user
        )
        return success_response(self.campaign_payload(campaign), "Collection campaign closed.")


class SubmissionDetailAPIView(DataCaptureAPIView):
    def get(self, request, request_id):
        data_request = self.get_readable_request(request_id)
        return success_response(SubmissionSerializer(data_request.submission).data)


class SubmissionAnswerAPIView(DataCaptureAPIView):
    def patch(self, request, request_id):
        data_request = self.get_action_request(
            request_id, "data.enter", require_assignee=True
        )
        serializer = TypedValueWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = self.service_call(
            DataCaptureLifecycleService.save_scalar_answer,
            data_request.submission,
            actor=request.user,
            **serializer.validated_data,
        )
        return success_response(SubmissionSerializer(answer.submission).data, "Draft answer saved.")


class SubmissionTableRowsAPIView(DataCaptureAPIView):
    def post(self, request, request_id):
        data_request = self.get_action_request(
            request_id, "data.enter", require_assignee=True
        )
        serializer = TableRowWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = self.service_call(
            DataCaptureLifecycleService.save_table_row,
            data_request.submission,
            actor=request.user,
            **serializer.validated_data,
        )
        return created_response(SubmissionSerializer(row.answer.submission).data, "TABLE row saved.")


class SubmissionTableRowDetailAPIView(DataCaptureAPIView):
    def patch(self, request, request_id, row_id):
        data_request = self.get_action_request(
            request_id, "data.enter", require_assignee=True
        )
        row = get_object_or_404(
            AnswerTableRow.objects.select_related("answer__submission"),
            pk=row_id,
            answer__submission=data_request.submission,
        )
        serializer = TableRowWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = self.service_call(
            DataCaptureLifecycleService.save_table_row,
            data_request.submission,
            actor=request.user,
            row=row,
            **serializer.validated_data,
        )
        return success_response(SubmissionSerializer(updated.answer.submission).data, "TABLE row saved.")

    def delete(self, request, request_id, row_id):
        data_request = self.get_action_request(
            request_id, "data.enter", require_assignee=True
        )
        row = get_object_or_404(
            AnswerTableRow.objects.select_related("answer__submission"),
            pk=row_id,
            answer__submission=data_request.submission,
        )
        self.service_call(
            DataCaptureLifecycleService.delete_table_row,
            data_request.submission,
            actor=request.user,
            row=row,
        )
        return success_response(message="TABLE row deleted.")


class SubmissionHistoryAPIView(DataCaptureAPIView):
    def get(self, request, request_id):
        data_request = self.get_readable_request(request_id)
        payload = {
            "request_events": DataRequestEventSerializer(
                data_request.events.select_related("actor", "previous_assignee", "assignee"), many=True
            ).data,
            "submission_events": SubmissionEventSerializer(
                data_request.submission.events.select_related("actor"), many=True
            ).data,
        }
        return success_response(payload)


class EvidenceListUploadAPIView(DataCaptureAPIView):
    """List scoped evidence metadata or upload draft evidence through storage."""

    def get(self, request, request_id):
        data_request = self.get_permission_scoped_request(request_id, "evidence.view")
        queryset = data_request.submission.evidence_files.select_related("answer", "uploaded_by")
        return self.paginated_success(queryset, EvidenceFileSerializer)

    def post(self, request, request_id):
        data_request = self.get_action_request(
            request_id, "evidence.upload", require_assignee=True
        )
        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence = self.service_call(
            EvidenceService.upload,
            data_request.submission,
            actor=request.user,
            uploaded_file=serializer.validated_data["file"],
            answer=serializer.validated_data.get("answer"),
        )
        return created_response(EvidenceFileSerializer(evidence).data, "Evidence uploaded.")


class EvidenceDetailAPIView(DataCaptureAPIView):
    def get_evidence(self, request_id, evidence_id, permission_code, *, require_assignee=False):
        if require_assignee:
            data_request = self.get_action_request(
                request_id, permission_code, require_assignee=True
            )
        else:
            data_request = self.get_permission_scoped_request(request_id, permission_code)
        return get_object_or_404(
            EvidenceFile.objects.select_related("answer", "uploaded_by", "submission"),
            pk=evidence_id,
            submission=data_request.submission,
        )

    def get(self, request, request_id, evidence_id):
        evidence = self.get_evidence(request_id, evidence_id, "evidence.view")
        return success_response(EvidenceFileSerializer(evidence).data)

    def delete(self, request, request_id, evidence_id):
        evidence = self.get_evidence(
            request_id, evidence_id, "evidence.upload", require_assignee=True
        )
        self.service_call(EvidenceService.delete, evidence, actor=request.user)
        return success_response(message="Evidence deleted.")


class EvidenceDownloadAPIView(EvidenceDetailAPIView):
    def get(self, request, request_id, evidence_id):
        evidence = self.get_evidence(request_id, evidence_id, "evidence.view")
        if not evidence.file or not evidence.file.storage.exists(evidence.file.name):
            raise NotFound("Evidence file not found.")
        return FileResponse(
            evidence.file.open("rb"),
            as_attachment=True,
            filename=evidence.original_filename,
            content_type=evidence.content_type,
        )


class SubmissionActionAPIView(DataCaptureAPIView):
    action_name = None
    permission_code = None
    needs_reason = False

    def post(self, request, request_id):
        data_request = self.get_action_request(
            request_id,
            self.permission_code,
            require_assignee=self.permission_code == "data.submit",
        )
        values = {}
        if self.needs_reason:
            serializer = ReasonSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            values = serializer.validated_data
        submission = self.service_call(
            getattr(DataCaptureLifecycleService, self.action_name),
            data_request.submission,
            actor=request.user,
            **values,
        )
        return success_response(SubmissionSerializer(submission).data, f"Submission {self.action_name}d.")


class SubmissionSubmitAPIView(SubmissionActionAPIView):
    action_name = "submit"
    permission_code = "data.submit"


class SubmissionApproveAPIView(SubmissionActionAPIView):
    action_name = "approve"
    permission_code = "data.approve"


class SubmissionRejectAPIView(SubmissionActionAPIView):
    action_name = "reject"
    permission_code = "data.approve"
    needs_reason = True


class SubmissionReopenAPIView(SubmissionActionAPIView):
    action_name = "reopen"
    permission_code = "data.approve"
    needs_reason = True
