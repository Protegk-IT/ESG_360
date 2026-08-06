from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import BaseModel
from apps.core.mixins import ActivityLogMixin
from django.core.exceptions import ValidationError

# apps/accounts/models.py

class User(ActivityLogMixin, AbstractUser):
    """
    Custom User model.
    Inherits:
        username
        password
        email
        is_active
        is_staff
        is_superuser
        last_login
        date_joined
        first_name
        last_name
    """

    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    employee_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    designation = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    profile_image = models.ImageField(
        upload_to="profile_images/",
        blank=True,
        null=True
    )

    last_seen = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        db_table = "users"
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        if self.full_name:
            return self.full_name
        return self.username

class Permission(ActivityLogMixin, BaseModel):
    """Permission Master with Module Hierarchy - 5 Modules Only""" 
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    module_code = models.CharField(max_length=100, blank=True, null=True)
    ACTION_CHOICES=(   
                ('MODULE_ACCESS', 'Module Access'),
                ('CREATE', 'Create'),
                ('EDIT', 'Edit'),
                ('VIEW', 'View'),
                ('DELETE', 'Delete'),
                ('APPROVE', 'Approve'),
                ('CLOSE', 'Close'),
                ('MANAGE', 'Manage'),
                ('EXPORT', 'Export'),
    )   
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES, 
        help_text="Type of permission"
    )

    display_order = models.IntegerField(default=0, help_text="Order to display in UI (lower = first)")

    class Meta:
        db_table = "permissions"
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["module_code"]),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_module_access(self):
        """Check if this is a module access permission"""
        return self.action == 'MODULE_ACCESS'

class Role(ActivityLogMixin, BaseModel):

    role_code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Unique code for the role"
    )

    role_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Display name of the role"
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True,
        blank=True,
    )

    is_system=models.BooleanField(
        default=False,
        help_text="System roles are seeded and cannot be deleted"
    )

    permissions = models.ManyToManyField(
        Permission,
        related_name="assigned_roles",
        blank=True
    )
    class Meta:
        db_table = "roles"
        ordering = ["role_name"]
        indexes = [
            models.Index(fields=["role_code"]),
        ]

    def __str__(self):
        return self.role_name
    
    def delete(self, *args, **kwargs):
        """
        Prevent deletion of system roles.
        """
        if self.is_system:
            raise ValidationError(
                "System roles cannot be deleted."
            )

        super().delete(*args, **kwargs)
    
class UserRoleAssignment(ActivityLogMixin, BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_assignments"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_assignments"
    )


    org_node = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Temporary Org Node Name"
    )

    module_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Null means access to all modules"
    )

    framework_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Null means access to all frameworks"
    )

    valid_from= models.DateField(
        null=True,
        blank=True,
    )

    valid_to = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "user_role_assignments"
        ordering = ["user", "role"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["role"]),
            models.Index(fields=["org_node"]),
        ]

        constraints = [
            models.UniqueConstraint(
            fields=[
                "user",
                "role",
                "org_node",
                "module_code",
                "framework_code",
        ],
        name="unique_role_assignment",
        )
    ]

    def __str__(self):
        return f"{self.user} - {self.role}"

class TestModel(ActivityLogMixin, BaseModel):
    name = models.CharField(max_length=100)


class UserDepartment(ActivityLogMixin, BaseModel):

    user=models.ForeignKey(
         User,
        on_delete=models.CASCADE,
        related_name="department_assignments"
    )

    department = models.CharField(
        max_length=100,
        db_index=True
    )

    is_primary=models.BooleanField(
        default=False
    )
    class Meta:
        db_table = "user_department"
        ordering = ["user"]
        indexes = [
            models.Index(fields=["user"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "department"],
                name="unique_user_department",
            )
        ]
    def __str__(self):
        return f"{self.user} - {self.department}"
    