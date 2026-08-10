from apps.core.models import Notification


def notify(
    recipient,
    notification_type,
    title,
    message,
    related_object=None,
    action_url=None,
    priority="NORMAL",
):
    """
    Create an in-app notification.
    """

    related_model = None
    related_object_id = None

    if related_object is not None:
        related_model = related_object.__class__.__name__
        related_object_id = str(related_object.pk)

    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_model=related_model,
        related_object_id=related_object_id,
        action_url=action_url,
        priority=priority,
    )