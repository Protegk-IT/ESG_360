
from rest_framework import serializers

from .models import User, Permissions, Role,UserRole, UserRoleScope


# ==========================
# Permission Serializer
# ==========================

class PermissionSerializer(serializers.ModelSerializer):

    permission_type_display = serializers.CharField(
        source="get_permission_type_display",
        read_only=True
    )

    class Meta:
        model = Permissions
        fields = [
            "id",
            "code",
            "name",
            "description",
            "permission_type",
            "permission_type_display",
            "display_order",
            "is_module_access",
        ]


# ==========================
# Role Serializer
# ==========================

class RoleSerializer(serializers.ModelSerializer):

    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permissions.objects.all(),
        many=True
    )

    permission_details = PermissionSerializer(
        source="permissions",
        many=True,
        read_only=True
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "role_code",
            "role_name",
            "description",
            "is_active",
            "permissions",
            "permission_details",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]

class UserRoleScopeSerializer(serializers.ModelSerializer):

    class Meta:

        model = UserRoleScope

        fields = [
            "id",
            "user_role",
            "scope_type",
            "scope_id"
        ]

class UserRoleSerializer(serializers.ModelSerializer):
    assigned_by = serializers.CharField(
        source="assigned_by.username",
        read_only=True
    )

    scopes = UserRoleScopeSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = UserRole
        fields = [
            "role",
            "assigned_by",
            "assigned_at",
            "scopes",
        ]


# ==========================
# User List Serializer
# ==========================

class UserSerializer(serializers.ModelSerializer):

    company_name = serializers.CharField(
        source="company.name",
        read_only=True
    )

    user_roles = UserRoleSerializer(
        many=True,
        read_only=True
    )

    role = RoleSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_code",
            "designation",
            "about",
            "company",
            "company_name",
            "role",
            "mobile_number",
            "profile_image",
            "is_company_user",
            "last_seen",
            "is_online",
            "is_active",
            "date_joined",
            "user_roles",
        ]


# ==========================
# User Create / Update
# ==========================

class UserCreateUpdateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=False
    )

    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = User
        fields = [
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_code",
            "designation",
            "about",
            "company",
            "role",
            "mobile_number",
            "profile_image",
            "is_company_user",
            "is_active",
        ]

    def create(self, validated_data):

        roles = validated_data.pop("role", [])

        password = validated_data.pop("password", None)

        user = User(**validated_data)

        if password:
            user.set_password(password)

        user.save()

        user.role.set(roles)

        return user

    def update(self, instance, validated_data):

        roles = validated_data.pop("role", None)

        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if roles is not None:
            instance.role.set(roles)

        return instance


# ==========================
# Login Serializer
# ==========================

class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()

    password = serializers.CharField(
        write_only=True
    )
