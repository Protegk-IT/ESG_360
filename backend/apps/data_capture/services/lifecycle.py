"""Transactional domain operations for generic data-capture workflow."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.data_capture.models import (
    Answer,
    AnswerTableCell,
    AnswerTableRow,
    DataRequest,
    DataRequestEvent,
    DataRequestStatus,
    Submission,
    SubmissionEvent,
    SubmissionStatus,
)
from apps.data_capture.validation import (
    expected_value_field,
    is_present,
    minimum_table_rows,
    validate_complete_value,
    validate_typed_value,
)
from apps.datapoints.models import DatapointDataType
from apps.periods.models import Status as PeriodStatus


class DataCaptureLifecycleService:
    """The only supported path for M5 workflow and draft mutations.

    Authorization by RBAC permissions/scope belongs to the future API layer.
    These operations still enforce domain ownership (the assignee is the maker)
    and maker-checker separation as non-negotiable workflow invariants.
    """

    @staticmethod
    def _ensure_period_open(context):
        reporting_period = getattr(context, "reporting_period", context)
        if reporting_period.status != PeriodStatus.OPEN:
            raise ValidationError("Reporting period is locked or closed.")

    @staticmethod
    def _ensure_maker(submission, actor):
        if submission.data_request.assignee_id != actor.id:
            raise PermissionDenied("Only the assigned user may change this draft.")

    @staticmethod
    def _ensure_assignee_can_capture(assignee, org_node):
        """Require one active assignment to grant capture and submit at this node.

        The two capabilities and OrgNode scope are evaluated from the same
        assignment, avoiding an unsafe cross-role permission/scope union.
        """

        if not assignee.is_active:
            raise ValidationError({"assignee": "Inactive users cannot be assigned data requests."})
        if assignee.is_superuser:
            return
        from apps.accounts.services.rbac import RBACService

        for assignment in RBACService.get_active_assignments(assignee):
            if assignment.module_code not in (None, "data"):
                continue
            permission_codes = {permission.code for permission in assignment.role.permissions.all()}
            if not {"data.enter", "data.submit"}.issubset(permission_codes):
                continue
            if assignment.org_node_id is None or org_node.path.startswith(assignment.org_node.path):
                return
        raise ValidationError({
            "assignee": "Assignee needs one active data.enter/data.submit assignment covering this OrgNode."
        })

    @classmethod
    @transaction.atomic
    def create_request(cls, *, actor, datapoint, org_node, reporting_period, assignee, due_date=None, instructions=""):
        cls._ensure_period_open(reporting_period)
        if not datapoint.is_active:
            raise ValidationError({"datapoint": "Inactive datapoints cannot receive data requests."})
        if not org_node.is_active:
            raise ValidationError({"org_node": "Inactive organization nodes cannot receive data requests."})
        cls._ensure_assignee_can_capture(assignee, org_node)
        try:
            # The database uniqueness constraint is the concurrency authority;
            # translate a competing create into a useful domain failure.
            with transaction.atomic():
                data_request = DataRequest.objects.create(
                    datapoint=datapoint,
                    org_node=org_node,
                    reporting_period=reporting_period,
                    assignee=assignee,
                    requested_by=actor,
                    due_date=due_date,
                    instructions=instructions,
                )
        except IntegrityError as exc:
            raise ValidationError({
                "non_field_errors": "A data request already exists for this datapoint, OrgNode, and reporting period."
            }) from exc
        DataRequestEvent.objects.create(
            data_request=data_request,
            event_type=DataRequestEvent.EventType.CREATED,
            actor=actor,
            assignee=assignee,
        )
        DataRequestEvent.objects.create(
            data_request=data_request,
            event_type=DataRequestEvent.EventType.ASSIGNED,
            actor=actor,
            assignee=assignee,
        )
        submission = Submission.objects.create(data_request=data_request)
        cls._event(submission, SubmissionEvent.EventType.CREATED, actor, "", SubmissionStatus.DRAFT)
        return data_request

    @classmethod
    @transaction.atomic
    def reassign_request(cls, data_request, *, actor, assignee, reason=""):
        # Lock via the same submission-first path used by every workflow write.
        submission = cls._locked_submission(data_request.submission)
        data_request = submission.data_request
        cls._ensure_period_open(data_request)
        if data_request.status != DataRequestStatus.OPEN:
            raise ValidationError("Only open data requests may be reassigned.")
        if submission.status != SubmissionStatus.DRAFT:
            raise ValidationError("A submitted request cannot be reassigned without reopening it.")
        cls._ensure_assignee_can_capture(assignee, data_request.org_node)
        previous_assignee = data_request.assignee
        data_request.assignee = assignee
        data_request._allow_reassignment = True
        try:
            data_request.save(update_fields=["assignee", "updated_at"])
        finally:
            del data_request._allow_reassignment
        DataRequestEvent.objects.create(
            data_request=data_request,
            event_type=DataRequestEvent.EventType.REASSIGNED,
            actor=actor,
            previous_assignee=previous_assignee,
            assignee=assignee,
            comment=reason,
        )
        return data_request

    @classmethod
    @transaction.atomic
    def save_scalar_answer(cls, submission, *, actor, **values):
        submission = cls._locked_submission(submission)
        cls._ensure_period_open(submission.data_request)
        cls._ensure_maker(submission, actor)
        if submission.status != SubmissionStatus.DRAFT:
            raise ValidationError("Only draft submissions may be edited.")
        if submission.datapoint.data_type == DatapointDataType.TABLE:
            raise ValidationError("Use table-row operations for a TABLE datapoint.")

        answer, _ = Answer.objects.get_or_create(submission=submission, defaults={"entered_by": actor})
        for field in (
            "decimal_value", "integer_value", "text_value", "boolean_value",
            "selected_option", "date_value", "unit",
        ):
            if field in values:
                setattr(answer, field, values[field])
        expected = expected_value_field(submission.datapoint)
        if (
            submission.datapoint.data_type in {DatapointDataType.DECIMAL, DatapointDataType.INTEGER}
            and is_present(getattr(answer, expected))
            and not answer.unit_id
            and submission.datapoint.default_unit_id
        ):
            answer.unit = submission.datapoint.default_unit
        answer.entered_by = actor
        answer.save()
        cls._event(submission, SubmissionEvent.EventType.DRAFT_SAVED, actor, SubmissionStatus.DRAFT, SubmissionStatus.DRAFT)
        return answer

    @classmethod
    @transaction.atomic
    def save_table_row(
        cls,
        submission,
        *,
        actor,
        definition_row=None,
        label=None,
        display_order=None,
        cells=(),
        row=None,
    ):
        submission = cls._locked_submission(submission)
        cls._ensure_period_open(submission.data_request)
        cls._ensure_maker(submission, actor)
        if submission.status != SubmissionStatus.DRAFT:
            raise ValidationError("Only draft submissions may be edited.")
        if submission.datapoint.data_type != DatapointDataType.TABLE:
            raise ValidationError("Table rows require a TABLE datapoint.")

        answer, _ = Answer.objects.get_or_create(submission=submission, defaults={"entered_by": actor})
        if row is not None:
            row = AnswerTableRow.objects.select_for_update().get(pk=row.pk)
            if row.answer_id != answer.id:
                raise ValidationError("TABLE row does not belong to this submission.")
            if definition_row is not None and definition_row.id != row.definition_row_id:
                raise ValidationError("A TABLE row's fixed-row identity cannot be changed.")
            if row.definition_row_id:
                row.label = row.definition_row.label
                row.display_order = row.definition_row.display_order
            else:
                if label is not None:
                    row.label = label
                if display_order is not None:
                    row.display_order = display_order
            row.save()
        elif definition_row:
            row, _ = AnswerTableRow.objects.update_or_create(
                answer=answer,
                definition_row=definition_row,
                # Fixed rows always derive their identity and ordering from M4;
                # callers do not need to echo those display-only values.
                defaults={
                    "label": definition_row.label,
                    "display_order": definition_row.display_order,
                },
            )
        else:
            if display_order is None:
                raise ValidationError({"display_order": "This field is required."})
            row = AnswerTableRow.objects.create(
                answer=answer, label=label or "", display_order=display_order
            )
        for cell_values in cells:
            cell_data = dict(cell_values)
            column = cell_data.pop("column")
            expected = expected_value_field(column)
            if (
                column.data_type in {DatapointDataType.DECIMAL, DatapointDataType.INTEGER}
                and is_present(cell_data.get(expected))
                and "unit" not in cell_data
                and column.default_unit_id
            ):
                cell_data["unit"] = column.default_unit
            defaults = cell_data
            AnswerTableCell.objects.update_or_create(row=row, column=column, defaults=defaults)
        cls._event(submission, SubmissionEvent.EventType.DRAFT_SAVED, actor, SubmissionStatus.DRAFT, SubmissionStatus.DRAFT)
        return row

    @classmethod
    @transaction.atomic
    def submit(cls, submission, *, actor):
        submission = cls._locked_submission(submission)
        cls._ensure_period_open(submission.data_request)
        cls._ensure_maker(submission, actor)
        if submission.status != SubmissionStatus.DRAFT:
            raise ValidationError("Only draft submissions may be submitted.")
        cls._validate_complete(submission)
        submission.status = SubmissionStatus.SUBMITTED
        submission.submitted_by = actor
        submission.submitted_at = timezone.now()
        cls._save_submission_transition(
            submission, update_fields=["status", "submitted_by", "submitted_at", "updated_at"]
        )
        cls._event(submission, SubmissionEvent.EventType.SUBMITTED, actor, SubmissionStatus.DRAFT, SubmissionStatus.SUBMITTED)
        return submission

    @classmethod
    @transaction.atomic
    def approve(cls, submission, *, actor):
        submission = cls._locked_submission(submission)
        cls._ensure_period_open(submission.data_request)
        if submission.status != SubmissionStatus.SUBMITTED:
            raise ValidationError("Only submitted submissions may be approved.")
        if submission.submitted_by_id == actor.id:
            raise PermissionDenied("A submitter may not approve their own submission.")
        submission.status = SubmissionStatus.APPROVED
        submission.approved_by = actor
        submission.approved_at = timezone.now()
        cls._save_submission_transition(
            submission, update_fields=["status", "approved_by", "approved_at", "updated_at"]
        )
        data_request = submission.data_request
        data_request.status = DataRequestStatus.COMPLETED
        cls._save_data_request_transition(data_request)
        cls._event(submission, SubmissionEvent.EventType.APPROVED, actor, SubmissionStatus.SUBMITTED, SubmissionStatus.APPROVED)
        return submission

    @classmethod
    @transaction.atomic
    def reject(cls, submission, *, actor, reason):
        if not reason or not reason.strip():
            raise ValidationError({"reason": "A rejection reason is required."})
        submission = cls._locked_submission(submission)
        cls._ensure_period_open(submission.data_request)
        if submission.status != SubmissionStatus.SUBMITTED:
            raise ValidationError("Only submitted submissions may be rejected.")
        if submission.submitted_by_id == actor.id:
            raise PermissionDenied("A submitter may not reject their own submission.")
        submission.status = SubmissionStatus.REJECTED
        submission.rejection_reason = reason.strip()
        submission.rejected_by = actor
        submission.rejected_at = timezone.now()
        cls._save_submission_transition(
            submission,
            update_fields=["status", "rejection_reason", "rejected_by", "rejected_at", "updated_at"],
        )
        cls._event(submission, SubmissionEvent.EventType.REJECTED, actor, SubmissionStatus.SUBMITTED, SubmissionStatus.REJECTED, reason=reason.strip())
        return submission

    @classmethod
    @transaction.atomic
    def reopen(cls, submission, *, actor, reason):
        if not reason or not reason.strip():
            raise ValidationError({"reason": "A reopen reason is required."})
        submission = cls._locked_submission(submission)
        cls._ensure_period_open(submission.data_request)
        if submission.status not in {SubmissionStatus.REJECTED, SubmissionStatus.APPROVED}:
            raise ValidationError("Only rejected or approved submissions may be reopened.")
        previous_status = submission.status
        submission.status = SubmissionStatus.DRAFT
        submission.reopened_by = actor
        submission.reopened_at = timezone.now()
        cls._save_submission_transition(
            submission, update_fields=["status", "reopened_by", "reopened_at", "updated_at"]
        )
        data_request = submission.data_request
        data_request.status = DataRequestStatus.OPEN
        cls._save_data_request_transition(data_request)
        cls._event(submission, SubmissionEvent.EventType.REOPENED, actor, previous_status, SubmissionStatus.DRAFT, reason=reason.strip())
        return submission

    @staticmethod
    def _locked_submission(submission):
        return Submission.objects.select_for_update().select_related(
            "data_request__datapoint", "data_request__reporting_period", "data_request__assignee"
        ).get(pk=submission.pk)

    @staticmethod
    def _event(submission, event_type, actor, from_status, to_status, *, reason="", details=None):
        return SubmissionEvent.objects.create(
            submission=submission,
            event_type=event_type,
            actor=actor,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            details=details or {},
        )

    @staticmethod
    def _save_submission_transition(submission, *, update_fields):
        submission._allow_lifecycle_transition = True
        try:
            submission.save(update_fields=update_fields)
        finally:
            del submission._allow_lifecycle_transition

    @staticmethod
    def _save_data_request_transition(data_request):
        data_request._allow_lifecycle_transition = True
        try:
            data_request.save(update_fields=["status", "updated_at"])
        finally:
            del data_request._allow_lifecycle_transition

    @staticmethod
    def _validate_complete(submission):
        datapoint = submission.datapoint
        try:
            answer = submission.answer
        except Answer.DoesNotExist as exc:
            if datapoint.is_required:
                raise ValidationError("A completed answer is required before submission.") from exc
            return

        if datapoint.data_type != DatapointDataType.TABLE:
            expected = expected_value_field(datapoint)
            if not is_present(getattr(answer, expected)):
                if datapoint.is_required:
                    raise ValidationError("A completed answer is required before submission.")
                validate_typed_value(answer, definition=datapoint)
                return
            validate_complete_value(answer, definition=datapoint)
            return

        rows = list(answer.table_rows.prefetch_related("cells__column", "definition_row"))
        fixed_rows = {row.definition_row_id for row in rows if row.definition_row_id}
        required_fixed_rows = set(datapoint.table_rows.values_list("id", flat=True))
        if rows and not required_fixed_rows.issubset(fixed_rows):
            raise ValidationError("All fixed TABLE rows must be completed before submission.")
        min_rows = minimum_table_rows(datapoint)
        if len(rows) < min_rows:
            raise ValidationError(f"At least {min_rows} TABLE rows are required before submission.")
        if datapoint.is_required and not rows:
            raise ValidationError("A completed TABLE answer is required before submission.")
        for row in rows:
            cells_by_column = {cell.column_id: cell for cell in row.cells.all()}
            for column in datapoint.table_columns.all():
                cell = cells_by_column.get(column.id)
                if column.is_required and cell is None:
                    raise ValidationError(f"{column.label} is required for every TABLE row.")
                if cell:
                    if column.is_required:
                        validate_complete_value(cell, definition=column, field_name="column")
                    else:
                        validate_typed_value(cell, definition=column, field_name="column")
