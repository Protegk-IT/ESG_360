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


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = (
        "batch",
        "row_number",
        "status",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "batch__file_name",
        "batch__id",
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