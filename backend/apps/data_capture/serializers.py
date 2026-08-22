"""Transport serializers for M5; lifecycle and value rules stay in services."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.datapoints.models import Datapoint, DatapointOption, DatapointTableColumn, DatapointTableRow, Unit
from apps.organizations.models import OrgNode
from apps.periods.models import ReportingPeriod

from .models import (
    Answer,
    AnswerTableCell,
    AnswerTableRow,
    DataRequest,
    DataRequestEvent,
    EvidenceFile,
    Submission,
    SubmissionEvent,
)


class DatapointReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datapoint
        fields = ("id", "code", "label", "data_type", "is_required", "allow_dynamic_rows")


class AnswerTableCellSerializer(serializers.ModelSerializer):
    column_code = serializers.CharField(source="column.code", read_only=True)
    column_label = serializers.CharField(source="column.label", read_only=True)

    class Meta:
        model = AnswerTableCell
        fields = (
            "id", "column", "column_code", "column_label", "decimal_value",
            "integer_value", "text_value", "boolean_value", "selected_option",
            "date_value", "unit",
        )
        read_only_fields = fields


class AnswerTableRowSerializer(serializers.ModelSerializer):
    cells = AnswerTableCellSerializer(many=True, read_only=True)

    class Meta:
        model = AnswerTableRow
        fields = ("id", "definition_row", "label", "display_order", "cells")
        read_only_fields = fields


class AnswerSerializer(serializers.ModelSerializer):
    table_rows = AnswerTableRowSerializer(many=True, read_only=True)

    class Meta:
        model = Answer
        fields = (
            "id", "decimal_value", "integer_value", "text_value", "boolean_value",
            "selected_option", "date_value", "unit", "entered_by", "table_rows",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class EvidenceFileSerializer(serializers.ModelSerializer):
    """Metadata only: the stored file path is never exposed by the API."""

    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = EvidenceFile
        fields = (
            "id", "submission", "answer", "original_filename", "content_type", "size",
            "uploaded_by", "uploaded_by_username", "created_at", "updated_at",
        )
        read_only_fields = fields


class SubmissionEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = SubmissionEvent
        fields = (
            "id", "event_type", "from_status", "to_status", "actor",
            "actor_username", "reason", "details", "created_at",
        )
        read_only_fields = fields


class DataRequestEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = DataRequestEvent
        fields = (
            "id", "event_type", "actor", "actor_username", "previous_assignee",
            "assignee", "comment", "created_at",
        )
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    answer = AnswerSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id", "status", "submitted_by", "submitted_at", "approved_by",
            "approved_at", "rejection_reason", "rejected_by", "rejected_at",
            "reopened_by", "reopened_at", "answer", "created_at", "updated_at",
        )
        read_only_fields = fields


class DataRequestSerializer(serializers.ModelSerializer):
    datapoint = DatapointReferenceSerializer(read_only=True)
    org_node_name = serializers.CharField(source="org_node.name", read_only=True)
    reporting_period_name = serializers.CharField(source="reporting_period.name", read_only=True)
    assignee_username = serializers.CharField(source="assignee.username", read_only=True)
    submission = SubmissionSerializer(read_only=True)

    class Meta:
        model = DataRequest
        fields = (
            "id", "datapoint", "org_node", "org_node_name", "reporting_period",
            "reporting_period_name", "module_code", "assignee", "assignee_username",
            "requested_by", "due_date", "status", "instructions", "submission",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class DataRequestListSerializer(serializers.ModelSerializer):
    """Deliberately light list payload; detail exposes the normalized answer."""

    datapoint_code = serializers.CharField(source="datapoint.code", read_only=True)
    datapoint_label = serializers.CharField(source="datapoint.label", read_only=True)
    org_node_name = serializers.CharField(source="org_node.name", read_only=True)
    reporting_period_name = serializers.CharField(source="reporting_period.name", read_only=True)
    assignee_username = serializers.CharField(source="assignee.username", read_only=True)
    submission_status = serializers.CharField(source="submission.status", read_only=True)

    class Meta:
        model = DataRequest
        fields = (
            "id", "datapoint", "datapoint_code", "datapoint_label", "org_node",
            "org_node_name", "reporting_period", "reporting_period_name", "module_code",
            "assignee", "assignee_username", "due_date", "status", "submission_status",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class DataRequestCreateSerializer(serializers.Serializer):
    datapoint = serializers.PrimaryKeyRelatedField(queryset=Datapoint.objects.all())
    org_node = serializers.PrimaryKeyRelatedField(queryset=OrgNode.objects.all())
    reporting_period = serializers.PrimaryKeyRelatedField(queryset=ReportingPeriod.objects.all())
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    due_date = serializers.DateField(required=False, allow_null=True)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")


class ReassignSerializer(serializers.Serializer):
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class TypedValueWriteSerializer(serializers.Serializer):
    """Only transports typed fields; M5 validation chooses the allowed field."""

    decimal_value = serializers.DecimalField(max_digits=24, decimal_places=8, required=False, allow_null=True)
    integer_value = serializers.IntegerField(required=False, allow_null=True)
    text_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    boolean_value = serializers.BooleanField(required=False, allow_null=True)
    selected_option = serializers.PrimaryKeyRelatedField(
        queryset=DatapointOption.objects.all(), required=False, allow_null=True
    )
    date_value = serializers.DateField(required=False, allow_null=True)
    unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all(), required=False, allow_null=True)

    value_fields = frozenset({
        "decimal_value", "integer_value", "text_value", "boolean_value",
        "selected_option", "date_value", "unit",
    })

    def to_internal_value(self, data):
        unknown = set(data) - self.value_fields
        if unknown:
            raise serializers.ValidationError({
                field: "This field is not writable on a draft answer."
                for field in sorted(unknown)
            })
        return super().to_internal_value(data)


class TableCellWriteSerializer(TypedValueWriteSerializer):
    column = serializers.PrimaryKeyRelatedField(queryset=DatapointTableColumn.objects.all())
    value_fields = TypedValueWriteSerializer.value_fields | {"column"}


class TableRowWriteSerializer(serializers.Serializer):
    definition_row = serializers.PrimaryKeyRelatedField(
        queryset=DatapointTableRow.objects.all(), required=False, allow_null=True
    )
    label = serializers.CharField(required=False, allow_blank=True, default="")
    display_order = serializers.IntegerField(required=False, min_value=0)
    cells = TableCellWriteSerializer(many=True, required=False, default=list)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True)


class EvidenceUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    answer = serializers.PrimaryKeyRelatedField(
        queryset=Answer.objects.all(), required=False, allow_null=True
    )
