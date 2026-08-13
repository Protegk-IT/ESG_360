from copy import copy

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

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


class ValidatedModelSerializer(serializers.ModelSerializer):
    """Run a model's cross-field validation during DRF validation.

    Django REST Framework validates fields and model uniqueness, but does not
    call ``Model.clean()``. These domain models intentionally keep their
    business rules there so non-API callers and API callers share one source
    of truth.
    """

    def validate(self, attrs):
        # Validation must not mutate ``self.instance``. DRF may reuse it after
        # an invalid partial update, so validate against a shallow model copy.
        instance = copy(self.instance) if self.instance is not None else self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            raise serializers.ValidationError(detail) from exc
        return attrs


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
