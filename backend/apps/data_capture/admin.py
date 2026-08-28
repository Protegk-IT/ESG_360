from django.contrib import admin

from .models import DataRequest, Submission


@admin.register(DataRequest)
class DataRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "datapoint",
        "org_node",
        "reporting_period",
        "module_code",
        "assignee",
        "status",
    )
    list_filter = (
        "status",
        "module_code",
        "reporting_period",
    )
    search_fields = (
        "datapoint__code",
        "org_node__code",
        "assignee__username",
    )


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "data_request",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "data_request__datapoint__code",
        "data_request__org_node__code",
    )