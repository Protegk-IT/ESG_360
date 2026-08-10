from django import forms
from django.contrib import admin

from .models import OrgNode



class OrgNodeAdminForm(forms.ModelForm):
    class Meta:
        model = OrgNode
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["parent"].label_from_instance = (
            lambda obj: f"{obj.path} ({obj.node_type})"
        )

@admin.register(OrgNode)
class OrgNodeAdmin(admin.ModelAdmin):
    form = OrgNodeAdminForm
    list_display = (
        "name",
        "node_type",
        "company",
        "parent",
        "depth",
        "path",
        "is_active",
    )
    list_filter = ("node_type", "is_active", "company")
    search_fields = ("name", "code", "company__company_name")
