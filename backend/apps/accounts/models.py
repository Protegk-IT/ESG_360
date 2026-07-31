from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

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

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    role = models.ManyToManyField(
    'accounts.Role',
    through='UserRole',
    through_fields=('user', 'role'),
    related_name='users',
    blank=True
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

class Permissions(models.Model):
    """Permission Master with Module Hierarchy - 5 Modules Only"""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    permission_type = models.CharField(
        max_length=20,
        choices=[
            ('MODULE_ACCESS', 'Module Access'),
            ('CREATE', 'Create'),
            ('EDIT', 'Edit'),
            ('VIEW', 'View'),
            ('DELETE', 'Delete'),
            ('APPROVE', 'Approve'),
            ('CLOSE', 'Close'),
            ('MANAGE', 'Manage'),
            ('EXPORT', 'Export'),
        ],
        default='VIEW',
        help_text="Type of permission"
    )
    display_order = models.IntegerField(default=0, help_text="Order to display in UI (lower = first)")

    class Meta:
        ordering = ['name', 'display_order', 'code']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_module_access(self):
        """Check if this is a module access permission"""
        return self.permission_type == 'MODULE_ACCESS'

class Role(models.Model):

    role_code = models.CharField(
        max_length=30,
        unique=True
    )

    role_name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    permissions = models.ManyToManyField(
        Permissions,
        related_name='roles',
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.role_name

    
class UserRole(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_roles"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_users"
    )

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role")


class UserRoleScope(models.Model):

    SCOPE_TYPES = (
        ("facility", "Facility"),
        ("category", "Category"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user_role = models.ForeignKey(
        "UserRole",
        on_delete=models.CASCADE,
        related_name="scopes"
    )

    scope_type = models.CharField(
        max_length=50,
        choices=SCOPE_TYPES
    )

    scope_id = models.CharField(
        max_length=100
    )


    class Meta:
        db_table = "user_role_scope"


    def __str__(self):
        return f"{self.user_role} - {self.scope_type}"
