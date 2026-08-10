from rest_framework import serializers

from apps.core.serializers import ValidatedModelSerializer

from .models import ReportingPeriod


class ReportingPeriodSerializer(ValidatedModelSerializer):
    class Meta:
        model = ReportingPeriod
        fields = [
            "id",
            "parent",
            "name",
            "period_type",
            "start_date",
            "end_date",
            "status",
            "is_baseline_year",
            "locked_at",
            "locked_by",
            "is_active",
            "created_at",
            "updated_at",
            "is_editable",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "locked_at",
            "is_editable",
        ]
