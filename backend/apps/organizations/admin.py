from django.contrib import admin

from .models import OrgNode


@admin.register(OrgNode)
class OrgNodeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "node_type",
        "company",
        "parent",
        "is_active",
    )
    list_filter = ("node_type", "is_active", "company")
    search_fields = ("name", "node_code", "company__company_name")
