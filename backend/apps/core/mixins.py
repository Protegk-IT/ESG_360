from datetime import date, datetime
from decimal import Decimal
import uuid
from django.db.models.fields.files import FieldFile
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

        if isinstance(value, (list, tuple, set)):
            return list(value)

        if hasattr(value, "pk"):
            return str(value.pk)

        return value
    
    def save(self, *args, **kwargs):
        is_create = self._state.adding
        old_data = {}

        # Capture old values before saving
        if not is_create:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_data = model_to_dict(old_instance)
            except self.__class__.DoesNotExist:
                old_data = {}

        # Save object
        super().save(*args, **kwargs)

        # Capture new values
        new_data = model_to_dict(self)

        if is_create:

            action = "CREATE"

            changes = {
                key: self._serialize_value(value)
                for key, value in new_data.items()
                if key not in self.EXCLUDED_FIELDS
            }

        else:

            action = "UPDATE"
            changes = {}

            for field, new_value in new_data.items():

                if field in self.EXCLUDED_FIELDS:
                    continue

                old_value = old_data.get(field)

                if old_value != new_value:

                    changes[field] = {
                        "old": self._serialize_value(old_value),
                        "new": self._serialize_value(new_value),
                    }

            # Don't create UPDATE log if nothing changed
            if not changes:
                return

        # Get request information
        request = get_current_request()

        user = None
        ip_address = None
        user_agent = ""

        if request:

            if hasattr(request, "user") and request.user.is_authenticated:
                user = request.user

            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")

        ActivityLog.objects.create(
            user=user,
            action=action,
            model_name=self.__class__.__name__,
            object_id=str(self.pk),
            object_repr=str(self),
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request.path if request else "",
        )

    def delete(self, *args, **kwargs):

        request = get_current_request()

        user = None
        ip_address = None
        user_agent = ""

        if request:

            if hasattr(request, "user") and request.user.is_authenticated:
                user = request.user

            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")

        ActivityLog.objects.create(
            user=user,
            action="DELETE",
            model_name=self.__class__.__name__,
            object_id=str(self.pk),
            object_repr=str(self),
            changes={},
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request.path if request else "",
        )

        return super().delete(*args, **kwargs)