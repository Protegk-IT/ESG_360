from django.contrib import admin

from apps.data_capture.models import (
    DataRequest,
    DataRequestEvent,
    Submission,
    SubmissionEvent,
    Answer,
    AnswerTableRow,
    AnswerTableCell,
    EvidenceFile,
)


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """Inspection-only: M5 mutations must go through the lifecycle/evidence
    services, never through Django admin's default add/change/delete forms.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(DataRequest)
class DataRequestAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "datapoint", "org_node", "assignee", "status", "due_date")
    list_filter = ("status",)
    search_fields = ("id", "datapoint__code", "assignee__username")


@admin.register(DataRequestEvent)
class DataRequestEventAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "event_type", "actor", "created_at")
    list_filter = ("event_type",)


@admin.register(Submission)
class SubmissionAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "data_request", "status", "submitted_by", "submitted_at")
    list_filter = ("status",)


@admin.register(SubmissionEvent)
class SubmissionEventAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "submission", "event_type", "actor", "created_at")
    list_filter = ("event_type",)


@admin.register(Answer)
class AnswerAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "submission", "entered_by", "updated_at")


@admin.register(AnswerTableRow)
class AnswerTableRowAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "answer", "label", "display_order")


@admin.register(AnswerTableCell)
class AnswerTableCellAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "row", "column")


@admin.register(EvidenceFile)
class EvidenceFileAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "submission", "original_filename", "uploaded_by", "created_at")