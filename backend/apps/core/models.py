import uuid
from django.db import models
from django.conf import settings

class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityLog(BaseModel):

    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),  
        ("EXPORT", "Export"),
        ("GENERATE", "Generate"),
        ("LOCK", "Lock"),
        ("UNLOCK", "Unlock"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    model_name = models.CharField(max_length=100)

    object_id = models.CharField(max_length=100)

    object_repr = models.CharField(max_length=255)

    changes = models.JSONField(default=dict)

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    request_path = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["model_name"]),
            models.Index(fields=["created_at"]),
        ]

class Notification(BaseModel):

    PRIORITY_CHOICES = (
        ("LOW", "Low"),
        ("NORMAL", "Normal"),
        ("HIGH", "High"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=100,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    related_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    related_object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    action_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="NORMAL",
    )

    is_read = models.BooleanField(
        default=False,
    )

    read_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    email_sent = models.BooleanField(
        default=False,
    )

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title