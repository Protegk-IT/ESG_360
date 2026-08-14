from django.contrib import admin

from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "esg_pillar",
        "is_core",
        "is_enabled",
        "display_order",
    )

    list_filter = (
        "esg_pillar",
        "is_core",
        "is_enabled",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    ordering = (
        "display_order",
        "name",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )