from datetime import date, datetime
from decimal import Decimal
import uuid
from django.db.models.fields.files import FieldFile, FileField
from django.db import transaction
from django.forms.models import model_to_dict

from .models import ActivityLog
from .thread_local import get_current_request


class ActivityLogMixin:
    """
    Automatically logs CREATE, UPDATE and DELETE operations.
    """

    EXCLUDED_FIELDS = {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "file",
    }

    SENSITIVE_FIELD_FRAGMENTS = (
        "password",
        "token",
        "secret",
        "api_key",
        "private_key",
    )

    def _is_excluded_field(self, field_name):
        normalized_name = field_name.lower()
        model_field = self._meta.get_field(field_name)
        return (
            normalized_name in self.EXCLUDED_FIELDS
            or normalized_name.endswith("_file")
            or isinstance(model_field, FileField)
            or any(fragment in normalized_name for fragment in self.SENSITIVE_FIELD_FRAGMENTS)
        )

    def _serialize_value(self, value):
        """
        Convert Python objects into JSON-serializable values.
        """ 

        if value is None:
            return None

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, uuid.UUID):
            return str(value)

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, FieldFile):
            return value.name if value else None

        if isinstance(value, dict):
            return {
                str(key): self._serialize_value(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [self._serialize_value(item) for item in value]

        if hasattr(value, "pk"):
            return str(value.pk)

        return value
    
    def _get_model_data(self):
        """Return the editable database fields that this audit mixin tracks."""
        return model_to_dict(self, fields=[field.name for field in self._meta.fields])

    def _get_request_metadata(self):
        request = get_current_request()
        if request is None:
            return None, None, "", ""

        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        return (
            user,
            request.META.get("REMOTE_ADDR"),
            request.META.get("HTTP_USER_AGENT", ""),
            request.path,
        )

    def _create_activity_log(self, *, action, changes, object_repr=None):
        user, ip_address, user_agent, request_path = self._get_request_metadata()
        ActivityLog.objects.create(
            user=user,
            action=action,
            model_name=self.__class__.__name__,
            object_id=str(self.pk),
            object_repr=object_repr if object_repr is not None else str(self),
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
        )

    def save(self, *args, **kwargs):
        is_create = self._state.adding
        old_data = {}

        update_fields = kwargs.get("update_fields")
        tracked_fields = None if update_fields is None else set(update_fields)

        # Capture old values before saving
        if not is_create:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_data = old_instance._get_model_data()
            except self.__class__.DoesNotExist:
                old_data = {}

        # The domain write and its log succeed or fail together. An audit
        # failure must not leave an un-audited write behind.
        with transaction.atomic():
            super().save(*args, **kwargs)

            # Capture new values after Django has persisted fields such as
            # auto-generated values.
            new_data = self._get_model_data()

            if is_create:
                action = "CREATE"
                changes = {
                    key: self._serialize_value(value)
                    for key, value in new_data.items()
                    if not self._is_excluded_field(key)
                }
            else:
                action = "UPDATE"
                changes = {}

                for field, new_value in new_data.items():
                    # With ``update_fields``, other changed Python attributes
                    # were deliberately not persisted and must not appear in
                    # the audit record as though they had been.
                    if tracked_fields is not None and field not in tracked_fields:
                        continue

                    if self._is_excluded_field(field):
                        continue

                    old_value = old_data.get(field)

                    if old_value != new_value:
                        changes[field] = {
                            "old": self._serialize_value(old_value),
                            "new": self._serialize_value(new_value),
                        }

                # Don't create UPDATE log if nothing changed.
                if not changes:
                    return

            self._create_activity_log(action=action, changes=changes)

    def delete(self, *args, **kwargs):
        object_repr = str(self)
        changes = {
            key: self._serialize_value(value)
            for key, value in self._get_model_data().items()
            if not self._is_excluded_field(key)
        }

        # Write the log before deletion so a deleted actor is still a valid
        # foreign-key target. The transaction rolls it back if deletion fails.
        with transaction.atomic():
            self._create_activity_log(
                action="DELETE",
                changes=changes,
                object_repr=object_repr,
            )
            return super().delete(*args, **kwargs)
