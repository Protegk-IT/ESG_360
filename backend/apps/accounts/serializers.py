from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.db import transaction
from apps.accounts.services.rbac import RBACService
from apps.companies.models import Department
from apps.organizations.models import OrgNode


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
            "is_system",
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
                # PUT includes unchanged read-only identity fields. Block a
                # real rename, not a normal permission-only update.
                if field in attrs and attrs[field] != getattr(self.instance, field):
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
   
    role_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    # Compatibility projection for the existing single-role editor. The full
    # scoped assignment contract remains available in role_assignments.
    role = serializers.SerializerMethodField()
    org_node = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
       
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
               "role_name",
               "role",
               "org_node",
               "department_name",
               "mobile_number",
               "mobile_number",
               "profile_image",
               "last_seen",
               "is_active",
               "is_staff",
               "is_superuser",
               "date_joined",
               "role_assignments",
               "department_assignments",
               "department",
           )
   
           read_only_fields = fields
   
    def validate_employee_code(self, value):
           if value:
               value = value.strip().upper()
           return value
   
    def get_role_name(self, obj):
           assignment = self._get_editor_assignment(obj)
           return assignment.role.role_name if assignment else None

    def _get_editor_assignment(self, obj):
        return (
            obj.user_assignments.filter(is_active=True)
            .select_related("role")
            .order_by("created_at", "id")
            .first()
        )

    def get_role(self, obj):
        assignment = self._get_editor_assignment(obj)
        return assignment.role_id if assignment else None

    def get_org_node(self, obj):
        assignment = self._get_editor_assignment(obj)
        return assignment.org_node_id if assignment else None
   
    def get_department_name(self, obj):
        assignment = obj.department_assignments.filter(is_primary=True).first()
        return assignment.department.name if assignment else None

    def get_department(self, obj):
        assignment = obj.department_assignments.filter(is_primary=True).first()
        return assignment.department_id if assignment else None

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
                    OrgNodeSerializer(assignment.org_node).data
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

    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    # Keep CharField and convert manually
    org_node = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    department = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "confirm_password",
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
            "role",
            "org_node",
            "department",
        )

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.pop("confirm_password", None)

        if password:
            if password != confirm_password:
                raise serializers.ValidationError(
                    {
                        "confirm_password": [
                            "Passwords do not match."
                        ]
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("role", None)
        org_node = validated_data.pop("org_node", None)
        department = validated_data.pop("department", None)
        password = validated_data.pop("password", None)

        user = User(**validated_data)

        if password:
            user.set_password(password)

        user.save()

        self._sync_role_assignment(user, role, org_node)
        self._sync_department(user, department)

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        role = validated_data.pop("role", None)
        org_node = validated_data.pop("org_node", None)
        department = validated_data.pop("department", None)
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        self._sync_role_assignment(instance, role, org_node)
        self._sync_department(instance, department)

        return instance

    def _sync_role_assignment(self, user, role, org_node):
        if role is None:
            return

        if org_node:
            try:
                org_node = OrgNode.objects.get(pk=org_node)
            except OrgNode.DoesNotExist:
                raise serializers.ValidationError(
                    {"org_node": "Invalid organization node."}
                )
        else:
            org_node = None

        UserRoleAssignment.objects.update_or_create(
            user=user,
            role=role,
            org_node=org_node,
            module_code=None,
            framework_code=None,
            defaults={
                "is_active": True,
            },
        )

    def _sync_department(self, user, department):
        if not department:
            return

        try:
            department = Department.objects.get(pk=department)
        except Department.DoesNotExist:
            raise serializers.ValidationError(
                {"department": "Invalid department."}
            )

        UserDepartment.objects.update_or_create(
            user=user,
            department=department,
            defaults={
                "is_primary": True,
            },
        )
        UserDepartment.objects.filter(user=user).exclude(
            department=department
        ).update(is_primary=False)

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
