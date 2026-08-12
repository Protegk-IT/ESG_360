from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class ESGPillar(models.TextChoices):
    E = "E", "E"
    S = "S", "S"
    G = "G", "G"
    PLATFORM = "PLATFORM", "Platform"


class Module(BaseModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable machine-readable module identifier.",
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
        default="",    )

    esg_pillar = models.CharField(
        max_length=10,
        choices=ESGPillar.choices,
        default=ESGPillar.PLATFORM,
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    is_core = models.BooleanField(
        default=False,
        help_text="Core modules cannot be disabled.",
    )

    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this module is enabled in this deployment.",
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["display_order", "name"]

    def clean(self):
        super().clean()

        if self.is_core and not self.is_enabled:
            raise ValidationError(
                {
                    "is_enabled": "Core modules cannot be disabled."
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"