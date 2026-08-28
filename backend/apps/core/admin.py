from django.contrib import admin
from .models import ActivityLog,Notification


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "user",
        "model_name",
        "object_id",
        "ip_address",
    )

    list_filter = (
        "action",
        "model_name",
        "created_at",
    )

    search_fields = (
        "user__username",
        "model_name",
        "object_id",
    )

    readonly_fields = [field.name for field in ActivityLog._meta.fields]

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "notification_type",
        "priority",
        "is_read",
        "email_sent",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "priority",
        "is_read",
        "email_sent",
    )

    search_fields = (
        "title",
        "message",
        "recipient__username",
    )

    readonly_fields = [field.name for field in Notification._meta.fields]

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False