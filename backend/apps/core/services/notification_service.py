from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.core.models import Notification


@transaction.atomic
def notify(
    *,
    recipient,
    notification_type,
    title,
    message,
    related_object=None,
    related_model=None,
    related_object_id=None,
    action_url=None,
    priority=Notification.PRIORITY_NORMAL,
):
    """
    Create and persist an in-app notification.

    This is the supported service boundary for other backend modules.
    Calling modules should use this function instead of creating
    Notification records directly.

    Related objects remain intentionally generic. No foreign key is
    created to the related domain object.
    """
    User = get_user_model()

    if not isinstance(recipient, User):
        raise ValidationError(
            {"recipient": "Recipient must be a valid user."}
        )

    if not isinstance(notification_type, str) or not notification_type.strip():
        raise ValidationError(
            {"notification_type": "Notification type is required."}
        )

    if not isinstance(title, str) or not title.strip():
        raise ValidationError(
            {"title": "Notification title is required."}
        )

    if not isinstance(message, str) or not message.strip():
        raise ValidationError(
            {"message": "Notification message is required."}
        )

    if priority not in {
        Notification.PRIORITY_LOW,
        Notification.PRIORITY_NORMAL,
        Notification.PRIORITY_HIGH,
    }:
        raise ValidationError(
            {
                "priority": (
                    "Priority must be one of: LOW, NORMAL, HIGH."
                )
            }
        )

    if related_object is not None and (
        related_model is not None or related_object_id is not None
    ):
        raise ValidationError(
            {
                "related_object": (
                    "Use either related_object or "
                    "related_model/related_object_id, not both."
                )
            }
        )

    if related_object is not None:
        related_model = related_object.__class__.__name__
        related_object_id = str(related_object.pk)

    if related_model is not None and not related_model:
        raise ValidationError(
            {
                "related_model": (
                    "Related model cannot be empty when supplied."
                )
            }
        )

    if related_object_id is not None and not related_object_id:
        raise ValidationError(
            {
                "related_object_id": (
                    "Related object ID cannot be empty when supplied."
                )
            }
        )

    notification = Notification(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_model=related_model,
        related_object_id=related_object_id,
        action_url=action_url,
        priority=priority,
        is_read=False,
        read_at=None,
        email_sent=False,
    )

    notification.full_clean()
    notification.save()

    return notification