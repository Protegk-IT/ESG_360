from rest_framework import serializers

from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )
from rest_framework import serializers
from apps.core.models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "recipient",
        )