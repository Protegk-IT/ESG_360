from rest_framework import serializers

from .models import Permissions, Role, User


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True
    )

    role_name = serializers.CharField(
        source="role.name",
        read_only=True
    )

    assigned_plants = serializers.StringRelatedField(
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
            "department",
            "department_name",
            "designation",
            "about",
            "company",
            "company_name",
            "role",
            "role_name",
            "assigned_plants",
            "mobile_number",
            "profile_image",
            "is_company_user",
            "last_seen",
            "is_online",
            "is_active",
            "date_joined",
        ]


class UserCreateUpdateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
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
            "department",
            "designation",
            "about",
            "company",
            "role",
            "assigned_plants",
            "mobile_number",
            "profile_image",
            "is_company_user",
            "is_active",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        plants = validated_data.pop("assigned_plants", [])

        user = User(**validated_data)

        if password:
            user.set_password(password)

        user.save()

        user.assigned_plants.set(plants)

        return user

    def update(self, instance, validated_data):

        password = validated_data.pop("password", None)

        plants = validated_data.pop("assigned_plants", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if plants is not None:
            instance.assigned_plants.set(plants)

        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        required=True
    )

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"}
    )

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

class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permissions.objects.all()
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