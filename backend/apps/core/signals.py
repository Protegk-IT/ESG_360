from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import ActivityLog


@receiver(user_logged_in)
def login_handler(sender, request, user, **kwargs):

    ActivityLog.objects.create(
        user=user,
        action="LOGIN",
        model_name="User",
        object_id=str(user.pk),
        object_repr=str(user),
        changes={},
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        request_path=request.path,
    )


@receiver(user_logged_out)
def logout_handler(sender, request, user, **kwargs):

    ActivityLog.objects.create(
        user=user,
        action="LOGOUT",
        model_name="User",
        object_id=str(user.pk),
        object_repr=str(user),
        changes={},
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        request_path=request.path,
    )