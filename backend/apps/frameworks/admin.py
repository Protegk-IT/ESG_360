from django.contrib import admin

from .models import (
    Framework,
    FrameworkNode,
    FrameworkVersion,
    DatapointMapping,
)


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_enabled",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
    )

    list_filter = (
        "is_enabled",
    )


@admin.register(FrameworkVersion)
class FrameworkVersionAdmin(admin.ModelAdmin):
    list_display = (
        "framework",
        "version_code",
        "version_name",
        "effective_from",
        "effective_to",
        "is_active",
        "is_default",
    )

    search_fields = (
        "framework__code",
        "version_code",
        "version_name",
    )

    list_filter = (
        "framework",
        "is_active",
        "is_default",
    )


@admin.register(FrameworkNode)
class FrameworkNodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "framework_version",
        "parent",
        "node_type",
        "display_order",
        "depth",
        "is_answerable",
        "is_core",
        "is_active",
    )

    search_fields = (
        "code",
        "title",
        "description",
    )

    list_filter = (
        "framework_version",
        "node_type",
        "is_answerable",
        "is_core",
        "is_active",
    )

    ordering = (
        "framework_version",
        "path",
        "display_order",
    )

@admin.register(DatapointMapping)
class DatapointMappingAdmin(admin.ModelAdmin):
    list_display = (
        "framework_node",
        "datapoint",
        "mapping_type",
        "aggregation",
        "is_primary",
        "confidence",
        "reviewed_at",
    )

    search_fields = (
        "framework_node__code",
        "framework_node__title",
        "datapoint__code",
        "datapoint__label",
    )

    list_filter = (
        "mapping_type",
        "aggregation",
        "confidence",
        "is_primary",
    )

    autocomplete_fields = (
        "framework_node",
        "datapoint",
    )


