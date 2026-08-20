from django.contrib import admin

from .models import ImportBatch, ImportRow


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "file_name",
        "import_type",
        "status",
        "total_rows",
        "valid_rows",
        "error_rows",
        "uploaded_by",
        "uploaded_at",
        "committed_at",
    )

    list_filter = (
        "import_type",
        "status",
        "uploaded_at",
    )

    search_fields = (
        "file_name",
        "module_code",
        "uploaded_by__username",
    )

    readonly_fields = (
        "id",
        "file_name",
        "file_path",
        "uploaded_at",
        "total_rows",
        "valid_rows",
        "error_rows",
        "committed_at",
    )

    ordering = ("-uploaded_at",)

    def get_readonly_fields(self, request, obj=None):
        """
        Committed batches are immutable through the admin.

        For an uncommitted batch, retain the normal editable fields.
        """

        readonly_fields = list(
            super().get_readonly_fields(request, obj)
        )

        if obj and obj.status == ImportBatch.Status.COMMITTED:
            readonly_fields.extend(
                [
                    "import_type",
                    "module_code",
                    "org_node",
                    "reporting_period",
                    "status",
                    "uploaded_by",
                ]
            )

        return tuple(readonly_fields)

    def has_delete_permission(self, request, obj=None):
        """
        A committed batch must never be deleted through admin.
        """

        if obj and obj.status == ImportBatch.Status.COMMITTED:
            return False

        return super().has_delete_permission(request, obj)


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    """
    Import rows are immutable records of the import operation.
    They must not be created, edited, or deleted manually through admin.
    """

    list_display = (
        "batch",
        "row_number",
        "status",
        "errors",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "batch__file_name",
    )

    readonly_fields = (
        "id",
        "batch",
        "row_number",
        "raw_data",
        "status",
        "errors",
    )

    ordering = (
        "batch",
        "row_number",
    )

    def has_add_permission(self, request):
        """
        Import rows must only be created by the import service.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Import rows are read-only through admin.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Import rows cannot be deleted through admin.
        """
        return False