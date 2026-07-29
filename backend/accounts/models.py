from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    employee_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    designation = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    about = models.TextField(
        blank=True,
        null=True
    )

    mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    profile_image = models.ImageField(
        upload_to="profile_images/",
        blank=True,
        null=True
    )

    is_company_user = models.BooleanField(
        default=False
    )

    last_seen = models.DateTimeField(
        blank=True,
        null=True
    )

    is_online = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.username