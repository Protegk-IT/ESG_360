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
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        request_path=request.path if request else "",
    )


@receiver(user_logged_out)
def logout_handler(sender, request, user, **kwargs):

    # Django permits logout on an anonymous request, which has no actor to
    # record. Authenticated logout continues to be audited below.
    if user is None:
        return

    ActivityLog.objects.create(
        user=user,
        action="LOGOUT",
        model_name="User",
        object_id=str(user.pk),
        object_repr=str(user),
        changes={},
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        request_path=request.path if request else "",
    )
