from rest_framework import serializers

from apps.periods.models import ReportingPeriod
from apps.frameworks.models import FrameworkVersion

from .models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)


class ReportRunSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and retrieving M8 ReportRun records.

    A ReportRun connects:

        ReportingPeriod + FrameworkVersion + created_by

    The framework snapshot is created separately through the
    M8 freeze service/API.
    """

    reporting_period_name = serializers.CharField(
        source="reporting_period.name",
        read_only=True,
    )

    framework_code = serializers.CharField(
        source="framework_version.framework.code",
        read_only=True,
    )

    framework_version_code = serializers.CharField(
        source="framework_version.version_code",
        read_only=True,
    )

    framework_version_name = serializers.CharField(
        source="framework_version.version_name",
        read_only=True,
    )

    created_by_name = serializers.SerializerMethodField()

    is_frozen = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = ReportRun

        fields = [
            "id",
            "reporting_period",
            "reporting_period_name",
            "framework_version",
            "framework_code",
            "framework_version_code",
            "framework_version_name",
            "created_by",
            "created_by_name",
            "status",
            "is_frozen",
            "snapshot_frozen_at",
            "metadata",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_by_name",
            "reporting_period_name",
            "framework_code",
            "framework_version_code",
            "framework_version_name",
            "status",
            "is_frozen",
            "snapshot_frozen_at",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        """
        Return a useful display value for the requesting user.

        The exact user model is centralized in AUTH_USER_MODEL,
        so we avoid assuming a specific user implementation.
        """

        user = obj.created_by

        if not user:
            return None

        if hasattr(user, "get_full_name"):
            full_name = user.get_full_name()

            if full_name:
                return full_name

        return getattr(
            user,
            "username",
            str(user),
        )

    def validate(self, attrs):
        """
        Validate the reporting context before creating a run.

        M3 and M7 remain the source of truth for their own models.
        M8 only verifies that the selected objects are usable.
        """

        reporting_period = attrs.get(
            "reporting_period",
            getattr(
                self.instance,
                "reporting_period",
                None,
            ),
        )

        framework_version = attrs.get(
            "framework_version",
            getattr(
                self.instance,
                "framework_version",
                None,
            ),
        )

        errors = {}

        if reporting_period is None:
            errors["reporting_period"] = (
                "A reporting period is required."
            )

        if framework_version is None:
            errors["framework_version"] = (
                "A framework version is required."
            )



        if errors:
            raise serializers.ValidationError(errors)

        # --------------------------------------------------------------
        # Frozen ReportRun protection
        # --------------------------------------------------------------

        if self.instance and self.instance.is_frozen:

            if (
                "reporting_period" in attrs
                and attrs["reporting_period"].pk
                != self.instance.reporting_period_id
            ):
                raise serializers.ValidationError(
                    {
                        "reporting_period": (
                            "Reporting period cannot be changed "
                            "after the report run is frozen."
                        )
                    }
                )

            if (
                "framework_version" in attrs
                and attrs["framework_version"].pk
                != self.instance.framework_version_id
            ):
                raise serializers.ValidationError(
                    {
                        "framework_version": (
                            "Framework version cannot be changed "
                            "after the report run is frozen."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        """
        The authenticated user is supplied by the view.

        The serializer deliberately does not accept created_by
        from the API client.
        """

        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "An authenticated user is required."
            )

        return ReportRun.objects.create(
            created_by=request.user,
            **validated_data,
        )


class SnapshotMappingSerializer(
    serializers.ModelSerializer
):
    """
    Read-only representation of one frozen datapoint mapping.
    """

    snapshot_node_code = serializers.CharField(
        source="snapshot_node.code",
        read_only=True,
    )

    snapshot_node_title = serializers.CharField(
        source="snapshot_node.title",
        read_only=True,
    )

    class Meta:
        model = SnapshotMapping

        fields = [
            "id",
            "snapshot_node",
            "snapshot_node_code",
            "snapshot_node_title",
            "source_mapping_id",
            "source_datapoint_id",
            "canonical_datapoint_code",
            "mapping_type",
            "aggregation",
            "transform_expression",
            "is_primary",
            "confidence",
            "mapping_note",
            "reviewed_at",
            "display_order",
            "metadata",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class SnapshotNodeSerializer(
    serializers.ModelSerializer
):
    """
    Read-only representation of one frozen framework node.

    Mappings are nested inside the node so the API can expose
    the frozen reporting structure without requiring the client
    to make another request for every node.
    """

    parent_code = serializers.CharField(
        source="parent.code",
        read_only=True,
        allow_null=True,
    )

    mappings = SnapshotMappingSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SnapshotNode

        fields = [
            "id",
            "snapshot",
            "source_node_id",
            "parent",
            "parent_code",
            "code",
            "title",
            "description",
            "instructions",
            "node_type",
            "display_order",
            "depth",
            "path",
            "response_format",
            "is_answerable",
            "is_core",
            "is_active",
            "metadata",
            "mappings",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class FrameworkSnapshotSerializer(
    serializers.ModelSerializer
):
    """
    Read-only representation of a frozen framework snapshot.
    """

    report_run_id = serializers.UUIDField(
        source="report_run.id",
        read_only=True,
    )

    nodes = SnapshotNodeSerializer(
        many=True,
        read_only=True,
    )

    node_count = serializers.SerializerMethodField()

    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = FrameworkSnapshot

        fields = [
            "id",
            "report_run",
            "report_run_id",
            "source_framework_id",
            "source_framework_version_id",
            "framework_code",
            "framework_name",
            "version_code",
            "version_name",
            "frozen_at",
            "node_count",
            "mapping_count",
            "nodes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_node_count(self, obj):
        return obj.nodes.count()

    def get_mapping_count(self, obj):
        return SnapshotMapping.objects.filter(
            snapshot_node__snapshot=obj,
        ).count()


class ReportRunDetailSerializer(
    ReportRunSerializer
):
    """
    Detailed ReportRun representation.

    Includes the frozen framework snapshot when one exists.
    """

    framework_snapshot = FrameworkSnapshotSerializer(
        read_only=True,
    )

    class Meta(ReportRunSerializer.Meta):
        fields = ReportRunSerializer.Meta.fields + [
            "framework_snapshot",
        ]

        read_only_fields = (
            ReportRunSerializer.Meta.read_only_fields
            + [
                "framework_snapshot",
            ]
        )