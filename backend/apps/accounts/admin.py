from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Permission,
    Role,
    UserRoleAssignment,
    UserDepartment,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = (
        (None, {
            "fields": (
                "username",
                "password",
            )
        }),

        ("Personal Information", {
            "fields": (
                "first_name",
                "last_name",
                "full_name",
                "email",
                "mobile_number",
                "profile_image",
                "designation",
                "employee_code",
            )
        }),

        ("Important Dates", {
            "fields": (
                "last_login",
                "last_seen",
                "date_joined",
            )
        }),
    )


    add_fieldsets = (
        (
            None,
            {
                "classes": (
                    "wide",
                ),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "email",
                    "full_name",
                    "employee_code",
                    "designation",
                    "mobile_number",
                    "profile_image",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "module_code",
        "action",
    )

    search_fields = (
        "code",
        "name",
    )

    list_filter = (
        "module_code",
        "action",
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "role_code",
        "role_name",
        "is_system",
        "is_active",
    )

    search_fields = (
        "role_code",
        "role_name",
    )

    filter_horizontal = ("permissions",)


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "org_node",
        "module_code",
        "framework_code",
        "is_active",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "user__username",
        "role__role_name",
    )


@admin.register(UserDepartment)
class UserDepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "department",
        "is_primary",
    )

    list_filter = ("is_primary",)

    search_fields = (
        "user__username",
        "department",
    )