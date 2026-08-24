"""Transactional M5 collection-campaign orchestration.

Campaigns deliberately orchestrate normal :class:`DataRequest` records.  They
never carry a parallel capture/review lifecycle or a copied submission status.
"""

from collections import Counter

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.services.rbac import RBACService
from apps.datapoints.models import CollectionLevel
from apps.organizations.models import OrgNode
from apps.periods.models import Status as PeriodStatus

from ..authorization import has_scoped_permission
from ..models import (
    CampaignTarget,
    CollectionCampaign,
    CollectionCampaignEvent,
    CollectionCampaignStatus,
    DataRequest,
    DataRequestStatus,
    SubmissionStatus,
)
from .lifecycle import DataCaptureLifecycleService


class CollectionCampaignService:
    """The only mutation path for campaign generation and reassignment."""

    @staticmethod
    def _ensure_period_open(campaign):
        if campaign.reporting_period.status != PeriodStatus.OPEN:
            raise ValidationError("Reporting period is locked or closed.")

    @staticmethod
    def _ensure_manage_scope(actor, org_node):
        if not has_scoped_permission(actor, "data.manage", org_node.id):
            # A protected-object response is produced by the API layer.  The
            # service retains an unambiguous domain failure for non-HTTP use.
            raise PermissionDenied("data.manage does not cover this OrgNode.")

    @staticmethod
    def can_manage_company(actor, company):
        """Whether a manager has a real data.manage assignment in a company.

        Campaign metadata itself has no OrgNode.  This deliberately requires a
        qualifying company-wide assignment or one scoped node in that company;
        generation subsequently verifies every target individually.
        """

        if actor.is_superuser:
            return True
        allowed_nodes = RBACService.get_allowed_org_nodes(
            actor, "data.manage", module_code="data"
        )
        if allowed_nodes is None:
            return True
        return bool(allowed_nodes) and OrgNode.objects.filter(
            company=company, id__in=allowed_nodes
        ).exists()

    @classmethod
    @transaction.atomic
    def create_campaign(cls, *, actor, company, reporting_period, code, name,
                        default_due_date=None, default_instructions=""):
        if reporting_period.status != PeriodStatus.OPEN:
            raise ValidationError({"reporting_period": "Reporting period is locked or closed."})
        if not cls.can_manage_company(actor, company):
            raise PermissionDenied("You don't have permission to manage this company.")
        campaign = CollectionCampaign.objects.create(
            company=company,
            reporting_period=reporting_period,
            code=code,
            name=name,
            default_due_date=default_due_date,
            default_instructions=default_instructions,
            created_by=actor,
        )
        CollectionCampaignEvent.objects.create(
            campaign=campaign,
            event_type=CollectionCampaignEvent.EventType.CREATED,
            actor=actor,
        )
        return campaign

    @staticmethod
    def _validate_collection_level(datapoint, org_node):
        level = datapoint.collection_level
        compatible = (
            level == CollectionLevel.ANY
            or level == CollectionLevel.ORG_NODE
            or (level == CollectionLevel.FACILITY and org_node.node_type == "FACILITY")
            or (
                level == CollectionLevel.COMPANY
                and org_node.node_type == "LEGAL_ENTITY"
                and org_node.parent_id is None
            )
        )
        if not compatible:
            raise ValidationError({
                "org_node": (
                    f"Datapoint {datapoint.code} collection level {level} is not compatible "
                    f"with OrgNode {org_node.code}."
                )
            })

    @classmethod
    def _normalise_and_validate_targets(cls, campaign, actor, targets):
        if not targets:
            raise ValidationError({"targets": "At least one explicit target is required."})
        if campaign.status == CollectionCampaignStatus.CLOSED:
            raise ValidationError("Closed campaigns cannot generate requests.")
        cls._ensure_period_open(campaign)

        normalised = []
        seen = set()
        for index, target in enumerate(targets):
            datapoint = target["datapoint"]
            org_node = target["org_node"]
            assignee = target["assignee"]
            key = (datapoint.id, org_node.id)
            if key in seen:
                raise ValidationError({"targets": f"Target {index + 1} repeats the same datapoint and OrgNode."})
            seen.add(key)
            if not datapoint.is_active:
                raise ValidationError({"datapoint": f"Datapoint {datapoint.code} is inactive."})
            if not org_node.is_active:
                raise ValidationError({"org_node": f"OrgNode {org_node.code} is inactive."})
            if org_node.company_id != campaign.company_id:
                raise ValidationError({"org_node": "Campaign targets must belong to the campaign company."})
            cls._validate_collection_level(datapoint, org_node)
            cls._ensure_manage_scope(actor, org_node)
            DataCaptureLifecycleService._ensure_assignee_can_capture(assignee, org_node)
            normalised.append({
                "datapoint": datapoint,
                "org_node": org_node,
                "assignee": assignee,
                "due_date": target.get("due_date", campaign.default_due_date),
                "instructions": target.get("instructions", campaign.default_instructions),
            })
        return normalised

    @classmethod
    @transaction.atomic
    def generate_requests(cls, campaign, *, actor, targets):
        """Prevalidate then atomically create/link every explicit target.

        Existing requests are linked as ``EXISTING``.  Their assignee, due date,
        instructions and state are deliberately never overwritten.
        """

        campaign = CollectionCampaign.objects.select_for_update().select_related(
            "company", "reporting_period"
        ).get(pk=campaign.pk)
        normalised = cls._normalise_and_validate_targets(campaign, actor, targets)

        keys = [(item["datapoint"].id, item["org_node"].id) for item in normalised]
        datapoint_ids = {key[0] for key in keys}
        org_node_ids = {key[1] for key in keys}
        existing_requests = {
            (request.datapoint_id, request.org_node_id): request
            for request in DataRequest.objects.select_for_update().filter(
                reporting_period=campaign.reporting_period,
                datapoint_id__in=datapoint_ids,
                org_node_id__in=org_node_ids,
            ).select_related("submission")
        }
        existing_targets = {
            (target.datapoint_id, target.org_node_id): target
            for target in CampaignTarget.objects.select_for_update().filter(
                campaign=campaign,
                datapoint_id__in=datapoint_ids,
                org_node_id__in=org_node_ids,
            ).select_related("data_request")
        }

        # This comparison is intentionally before any writes.  A replay must
        # be identical; changing assignment/instructions is an explicit bulk
        # reassignment, not a hidden generation side effect.
        for target in normalised:
            prior = existing_targets.get((target["datapoint"].id, target["org_node"].id))
            if prior and (
                prior.assignee_id != target["assignee"].id
                or prior.due_date != target["due_date"]
                or prior.instructions != target["instructions"]
            ):
                raise ValidationError({
                    "targets": "An existing campaign target differs. Use controlled bulk reassignment or create a new campaign."
                })

        summary = Counter(created=0, existing=0, replayed=0)
        linked_targets = []
        for target in normalised:
            key = (target["datapoint"].id, target["org_node"].id)
            prior = existing_targets.get(key)
            if prior and prior.data_request_id:
                linked_targets.append(prior)
                summary["replayed"] += 1
                continue

            data_request = existing_requests.get(key)
            if data_request:
                outcome = CampaignTarget.RequestOutcome.EXISTING
                summary["existing"] += 1
            else:
                data_request = DataCaptureLifecycleService.create_request(
                    actor=actor,
                    datapoint=target["datapoint"],
                    org_node=target["org_node"],
                    reporting_period=campaign.reporting_period,
                    assignee=target["assignee"],
                    due_date=target["due_date"],
                    instructions=target["instructions"],
                )
                existing_requests[key] = data_request
                outcome = CampaignTarget.RequestOutcome.CREATED
                summary["created"] += 1

            if prior:
                prior.data_request = data_request
                prior.request_outcome = outcome
                prior.save(update_fields=["data_request", "request_outcome", "updated_at"])
                target_record = prior
            else:
                target_record = CampaignTarget.objects.create(
                    campaign=campaign,
                    datapoint=target["datapoint"],
                    org_node=target["org_node"],
                    assignee=target["assignee"],
                    due_date=target["due_date"],
                    instructions=target["instructions"],
                    data_request=data_request,
                    request_outcome=outcome,
                )
            linked_targets.append(target_record)

        if campaign.status == CollectionCampaignStatus.DRAFT:
            campaign.status = CollectionCampaignStatus.ACTIVE
        if campaign.generated_at is None:
            campaign.generated_at = timezone.now()
        campaign._allow_campaign_transition = True
        try:
            campaign.save(update_fields=["status", "generated_at", "updated_at"])
        finally:
            del campaign._allow_campaign_transition
        CollectionCampaignEvent.objects.create(
            campaign=campaign,
            event_type=CollectionCampaignEvent.EventType.GENERATED,
            actor=actor,
            details=dict(summary),
        )
        return linked_targets, dict(summary)

    @classmethod
    @transaction.atomic
    def bulk_reassign(cls, campaign, *, actor, target_ids, assignee, reason=""):
        campaign = CollectionCampaign.objects.select_for_update().select_related(
            "reporting_period"
        ).get(pk=campaign.pk)
        if campaign.status == CollectionCampaignStatus.CLOSED:
            raise ValidationError("Closed campaigns cannot be reassigned.")
        cls._ensure_period_open(campaign)
        targets = list(CampaignTarget.objects.select_for_update().select_related(
            "org_node", "data_request__submission"
        ).filter(campaign=campaign, id__in=target_ids))
        if not targets or len(targets) != len(set(target_ids)):
            raise ValidationError({"targets": "One or more campaign targets were not found."})

        # Prevalidate every target so a bad assignee/scope/status cannot leave
        # a partially reassigned campaign.
        for target in targets:
            if not target.data_request_id:
                raise ValidationError({"targets": "Campaign target has no generated request."})
            cls._ensure_manage_scope(actor, target.org_node)
            DataCaptureLifecycleService._ensure_assignee_can_capture(assignee, target.org_node)
            if target.data_request.status != DataRequestStatus.OPEN or target.data_request.submission.status != SubmissionStatus.DRAFT:
                raise ValidationError({"targets": "Only open draft requests may be reassigned."})

        for target in targets:
            DataCaptureLifecycleService.reassign_request(
                target.data_request, actor=actor, assignee=assignee, reason=reason
            )
            target.assignee = assignee
            target._allow_target_update = True
            try:
                target.save(update_fields=["assignee", "updated_at"])
            finally:
                del target._allow_target_update
        CollectionCampaignEvent.objects.create(
            campaign=campaign,
            event_type=CollectionCampaignEvent.EventType.REASSIGNED,
            actor=actor,
            details={"target_count": len(targets), "assignee_id": assignee.id, "reason": reason},
        )
        return targets

    @classmethod
    @transaction.atomic
    def close_campaign(cls, campaign, *, actor):
        campaign = CollectionCampaign.objects.select_for_update().get(pk=campaign.pk)
        if campaign.status == CollectionCampaignStatus.CLOSED:
            return campaign
        campaign.status = CollectionCampaignStatus.CLOSED
        campaign.closed_at = timezone.now()
        campaign._allow_campaign_transition = True
        try:
            campaign.save(update_fields=["status", "closed_at", "updated_at"])
        finally:
            del campaign._allow_campaign_transition
        CollectionCampaignEvent.objects.create(
            campaign=campaign,
            event_type=CollectionCampaignEvent.EventType.CLOSED,
            actor=actor,
        )
        return campaign

    @staticmethod
    def progress(targets):
        """Aggregate current linked M5 state without copying it to campaigns."""

        today = timezone.localdate()
        aggregate = targets.aggregate(
            total_targets=Count("id"),
            linked_requests=Count("data_request", distinct=True),
            open_requests=Count("id", filter=Q(data_request__status=DataRequestStatus.OPEN)),
            completed_requests=Count("id", filter=Q(data_request__status=DataRequestStatus.COMPLETED)),
            cancelled_requests=Count("id", filter=Q(data_request__status=DataRequestStatus.CANCELLED)),
            draft_submissions=Count("id", filter=Q(data_request__submission__status=SubmissionStatus.DRAFT)),
            submitted_submissions=Count("id", filter=Q(data_request__submission__status=SubmissionStatus.SUBMITTED)),
            approved_submissions=Count("id", filter=Q(data_request__submission__status=SubmissionStatus.APPROVED)),
            rejected_submissions=Count("id", filter=Q(data_request__submission__status=SubmissionStatus.REJECTED)),
            without_submission=Count("id", filter=Q(data_request__isnull=False, data_request__submission__isnull=True)),
            overdue=Count("id", filter=Q(
                data_request__due_date__lt=today,
                data_request__status=DataRequestStatus.OPEN,
            )),
        )
        return aggregate
