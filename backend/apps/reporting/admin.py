from django.contrib import admin

from .models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)


@admin.register(ReportRun)
class ReportRunAdmin(admin.ModelAdmin):
    """
    Admin configuration for M8 ReportRun.

    ReportRun represents one reporting execution context.
    """

    list_display = (
        "id",
        "reporting_period",
        "framework_version",
        "created_by",
        "status",
        "snapshot_frozen_at",
        "created_at",
    )

    search_fields = (
        "id",
        "reporting_period__name",
        "framework_version__framework__code",
        "framework_version__version_code",
        "framework_version__version_name",
        "created_by__username",
        "created_by__email",
    )

    list_filter = (
        "status",
        "reporting_period",
        "framework_version",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "snapshot_frozen_at",
    )


@admin.register(FrameworkSnapshot)
class FrameworkSnapshotAdmin(admin.ModelAdmin):
    """
    Admin configuration for immutable framework snapshots.

    Snapshots are created by the M8 freeze service and are
    read-only through Django Admin.
    """

    list_display = (
        "id",
        "report_run",
        "framework_code",
        "framework_name",
        "version_code",
        "version_name",
        "frozen_at",
        "created_at",
    )

    search_fields = (
        "id",
        "framework_code",
        "framework_name",
        "version_code",
        "version_name",
        "report_run__id",
    )

    list_filter = (
        "framework_code",
        "version_code",
    )

    ordering = (
        "-frozen_at",
    )

    readonly_fields = (
        "id",
        "report_run",
        "source_framework_id",
        "source_framework_version_id",
        "framework_code",
        "framework_name",
        "version_code",
        "version_name",
        "frozen_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        """
        Snapshots must be created only through the M8 freeze service.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Frozen snapshots are immutable.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Frozen snapshots cannot be deleted through admin.
        """
        return False


@admin.register(SnapshotNode)
class SnapshotNodeAdmin(admin.ModelAdmin):
    """
    Admin configuration for immutable frozen framework nodes.
    """

    list_display = (
        "id",
        "snapshot",
        "code",
        "title",
        "node_type",
        "parent",
        "display_order",
        "depth",
        "is_answerable",
        "is_core",
        "is_active",
    )

    search_fields = (
        "id",
        "code",
        "title",
        "description",
        "snapshot__framework_code",
        "snapshot__version_code",
    )

    list_filter = (
        "node_type",
        "is_answerable",
        "is_core",
        "is_active",
    )

    ordering = (
        "snapshot",
        "path",
        "display_order",
        "code",
    )

    readonly_fields = (
        "id",
        "snapshot",
        "parent",
        "source_node_id",
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
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        """
        Snapshot nodes are created only by the freeze service.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Snapshot nodes are immutable.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Snapshot nodes cannot be deleted through admin.
        """
        return False


@admin.register(SnapshotMapping)
class SnapshotMappingAdmin(admin.ModelAdmin):
    """
    Admin configuration for immutable frozen datapoint mappings.
    """

    list_display = (
        "id",
        "snapshot_node",
        "canonical_datapoint_code",
        "mapping_type",
        "aggregation",
        "is_primary",
        "confidence",
        "reviewed_at",
    )

    search_fields = (
        "id",
        "canonical_datapoint_code",
        "snapshot_node__code",
        "snapshot_node__title",
        "snapshot_node__snapshot__framework_code",
        "snapshot_node__snapshot__version_code",
    )

    list_filter = (
        "mapping_type",
        "aggregation",
        "confidence",
        "is_primary",
    )

    ordering = (
        "snapshot_node",
        "display_order",
        "canonical_datapoint_code",
    )

    readonly_fields = (
        "id",
        "snapshot_node",
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
    )

    def has_add_permission(self, request):
        """
        Snapshot mappings are created only by the freeze service.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Snapshot mappings are immutable.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Snapshot mappings cannot be deleted through admin.
        """
        return False