from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.services.rbac import RBACService

from .models import (
    User,
    Permission,
    Role,
    UserRoleAssignment,
    UserDepartment,
)
from apps.organizations.serializers import OrgNodeSerializer

class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = (
            "id",
            "code",
            "name",
            "module_code",
            "action",
            "display_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

class RoleSerializer(serializers.ModelSerializer):

    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        required=False,
    )

    permission_details = PermissionSerializer(
        source="permissions",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Role
        fields = (
            "id",
            "role_code",
            "role_name",
            "description",
            "is_active",
            "is_system",
            "permissions",
            "permission_details",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if self.instance and self.instance.is_system:
            protected = [
                "role_code",
                "role_name",
                "is_system",
            ]

            for field in protected:
                if field in attrs:
                    raise serializers.ValidationError(
                        f"{field} cannot be modified for a system role."
                    )

        return attrs


class UserRoleAssignmentSerializer(serializers.ModelSerializer):

    user_name = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    role_name = serializers.CharField(
        source="role.role_name",
        read_only=True,
    )

    org_node_name = serializers.CharField(
        source="org_node.name",
        read_only=True,
    )
    class Meta:
        model = UserRoleAssignment
        fields = (
            "id",
            "user",
            "user_name",
            "role",
            "role_name",
            "org_node",
            "org_node_name",
            "module_code",
            "framework_code",
            "valid_from",
            "valid_to",
            "is_active",
            "created_at",
            "updated_at",
            
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "user_name",
            "role_name",
            "org_node_name",
        )

    def validate(self, attrs):

        valid_from = attrs.get("valid_from",getattr(self.instance, "valid_from", None))
        valid_to = attrs.get("valid_to",getattr(self.instance, "valid_to", None))

        if valid_from and valid_to:
            if valid_from > valid_to:
                raise serializers.ValidationError(
                    {"valid_to": "Valid From cannot be after Valid To."}
                )

        return attrs

class UserDepartmentSerializer(serializers.ModelSerializer):

    user_name = serializers.CharField(
        source="user.username",
        read_only=True,
    )


    class Meta:
        model = UserDepartment
        fields = (
            "id",
            "user",
            "user_name",
            "department",
            "is_primary",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "user_name",
        )

class UserSerializer(serializers.ModelSerializer):

    role_assignments = UserRoleAssignmentSerializer(
        source="user_assignments",
        many=True,
        read_only=True,
    )

    department_assignments = UserDepartmentSerializer(
        many=True,
        read_only=True,
    )
    
    class Meta:
        model = User

        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_code",
            "designation",
            "mobile_number",
            "profile_image",
            "last_seen",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "role_assignments",
            "department_assignments",
        )

        read_only_fields = fields

    def validate_employee_code(self, value):
        if value:
            value = value.strip().upper()
        return value

class CurrentUserSerializer(UserSerializer):

    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    scope_summary = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            "roles",
            "permissions",
            "scope_summary",
        )

    def get_roles(self, obj):

        assignments = RBACService.get_active_assignments(obj)

        return list(
            assignments.values_list(
                "role__role_name",
                flat=True,
            ).distinct()
        )

    def get_permissions(self, obj):

        permissions = set()

        assignments = (
            RBACService.get_active_assignments(obj)
            .select_related("role")
            .prefetch_related("role__permissions")
        )

        for assignment in assignments:
            for permission in assignment.role.permissions.all():
                permissions.add(permission.code)

        return sorted(permissions)

    def get_scope_summary(self, obj):

        assignments = RBACService.get_active_assignments(obj)

        return [
            {
                "role": assignment.role.role_name,
                "org_node": (
                    OrgNodeSerializer(
                        assignment.org_node
                    ).data
                    if assignment.org_node
                    else None
                ),
                "module_code": assignment.module_code,
                "framework_code": assignment.framework_code,
                "valid_from": assignment.valid_from,
                "valid_to": assignment.valid_to,
            }
            for assignment in assignments
        ]

class UserCreateUpdateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
    )

    class Meta:
        model = User

        fields = (
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_code",
            "designation",
            "mobile_number",
            "profile_image",
            "is_active",
            "is_staff",
        )

    def create(self, validated_data):

        password = validated_data.pop("password", None)

        user = User(**validated_data)

        if password:
            user.set_password(password)

        user.save()

        return user

    def update(self, instance, validated_data):

        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        return instance

class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()

    password = serializers.CharField(
        write_only=True
    )
class ChangePasswordSerializer(serializers.Serializer):

    old_password = serializers.CharField(
        write_only=True
    )

    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )