from urllib import request
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.companies.models import Company, Department
from apps.organizations.models import OrgNode
from .permissions import HasRolePermission
from rest_framework import viewsets, status
from rest_framework.response import Response

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from apps.accounts.permissions import HasRolePermission
from rest_framework import viewsets
from apps.accounts.viewsets import RBACModelViewSet
from rest_framework.exceptions import PermissionDenied
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view


from .models import (
    User,
    Permission,
    Role,
    UserRoleAssignment,
    UserDepartment,
)

from .serializers import (
    UserSerializer,
    CurrentUserSerializer,
    UserCreateUpdateSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserRoleAssignmentSerializer,
    UserDepartmentSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
)


# ==========================================
# Permission CRUD
# ==========================================

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):

    permission_classes = [
        IsAuthenticated,
        HasRolePermission,
    ]

    module_code = "permission"

    queryset = Permission.objects.order_by(
        "module_code",
        "display_order",
    )

    serializer_class = PermissionSerializer

    def get_required_permission(self):
        return "permission.view"
# ==========================================
# Role CRUD
# ==========================================

class RoleViewSet(RBACModelViewSet):

    module_code = "role"

    queryset = (
        Role.objects
        .prefetch_related("permissions")
        .all()
    )

    serializer_class = RoleSerializer

    def initial(self, request, *args, **kwargs):
        """
        Only superusers can create, update or delete roles.
        """
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
        ):
            if not request.user.is_superuser:
                raise PermissionDenied(
                    "Only superusers can manage roles."
                )

        super().initial(request, *args, **kwargs)


        
class UserViewSet(RBACModelViewSet):

    module_code = "user"

    queryset = (
        User.objects
        .prefetch_related(
            "user_assignments__role",
            "department_assignments",
        )
        .all()
    )

    def get_serializer_class(self):

        if self.action in (
            "create",
            "update",
            "partial_update",
        ):
            return UserCreateUpdateSerializer

        return UserSerializer

    def get_required_permission(self):

        custom_permissions = {
            "deactivate": "user.edit",

            "assignments": {
                "GET": "user.view",
                "POST": "user.edit",
            },

            "assignment_detail": {
                "PATCH": "user.edit",
                "DELETE": "user.edit",
            },

            "departments": {
                "GET": "user.view",
                "POST": "user.edit",
            },

            "department_detail": {
                "DELETE": "user.edit",
            },
        }       

        if self.action in custom_permissions:
            return custom_permissions[self.action]

        return super().get_required_permission()

    # ==========================================
    # Deactivate User
    # ==========================================

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
    )
    def deactivate(self, request, pk=None):

        user = self.get_object()

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {
                "message": "User deactivated successfully."
            },
            status=status.HTTP_200_OK,
        )


    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a user by marking them inactive.
        """

        user = self.get_object()

        # Prevent deleting yourself (optional but recommended)
        if user == request.user:
            return Response(
                {
                    "detail": "You cannot deactivate your own account."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {
                    "detail": "User is already inactive."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {
                "message": "User deactivated successfully."
            },
            status=status.HTTP_200_OK,
        )

    # ==========================================
    # User Role Assignments
    # ==========================================

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="assignments",
    )
    def assignments(self, request, pk=None):

        user = self.get_object()

        if request.method == "GET":

            assignments = UserRoleAssignment.objects.filter(
                user=user
            ).select_related("role")

            serializer = UserRoleAssignmentSerializer(
                assignments,
                many=True,
            )

            return Response(serializer.data)

        serializer = UserRoleAssignmentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(user=user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # ==========================================
    # Assignment Detail
    # ==========================================

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"assignments/(?P<assignment_id>[^/.]+)",
    )
    def assignment_detail(
        self,
        request,
        pk=None,
        assignment_id=None,
    ):

        user = self.get_object()

        assignment = get_object_or_404(
            UserRoleAssignment,
            pk=assignment_id,
            user=user,
        )

        if request.method == "PATCH":

            serializer = UserRoleAssignmentSerializer(
                assignment,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(
                raise_exception=True
            )

            serializer.save()

            return Response(serializer.data)

        assignment.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

    # ==========================================
    # User Departments
    # ==========================================

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="departments",
    )
    def departments(self, request, pk=None):

        user = self.get_object()

        if request.method == "GET":

            departments = UserDepartment.objects.filter(
                user=user
            )

            serializer = UserDepartmentSerializer(
                departments,
                many=True,
            )

            return Response(serializer.data)

        serializer = UserDepartmentSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save(user=user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # ==========================================
    # Department Detail
    # ==========================================

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"departments/(?P<department_id>[^/.]+)",
    )
    def department_detail(
        self,
        request,
        pk=None,
        department_id=None,
    ):

        user = self.get_object()

        department = get_object_or_404(
            UserDepartment,
            pk=department_id,
            user=user,
        )

        department.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

# ==========================================
# CSRF Token
# ==========================================

class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "csrfToken": get_token(request)
        })
# ==========================================
# Login
# ==========================================

class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "csrfToken": get_token(request),
            },
            status=status.HTTP_200_OK,
        )
    
        csrf_token = get_token(request)

        return Response({
    "success": True,
    "message": "Login successful.",
    "csrf_token": csrf_token,
    "user": {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,

        # Super Admin
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,


        # Role Codes
        "roles": list(
            user.role.filter(is_active=True)
            .values_list("role_code", flat=True)
        ),

        # Permission Codes
        "permissions": list(
            user.role.filter(is_active=True)
            .values_list("permissions__code", flat=True)
            .distinct()
        ),
    }
})


# ==========================================
# Logout
# ==========================================

class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        logout(request)

        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )


# ==========================================
# Current User
# ==========================================

class CurrentUserView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = CurrentUserSerializer(request.user)

        return Response(serializer.data)


# ==========================================
# Change Password
# ==========================================

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = request.user

        if not user.check_password(
            serializer.validated_data["old_password"]
        ):
            return Response(
                {
                    "old_password": [
                        "Old password is incorrect."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(
            serializer.validated_data["new_password"]
        )
        user.save()

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )
        

# ==========================================
# USER DETAIL
# ==========================================

class UserDetailView(APIView):

    def get_permissions(self):

        if self.request.method == "GET":

            class Permission(HasRolePermission):
                permission_code = "user.view"

            return [Permission()]

        elif self.request.method in ["PUT", "PATCH"]:

            class Permission(HasRolePermission):
                permission_code = "user.edit"

            return [Permission()]

        elif self.request.method == "DELETE":

            class Permission(HasRolePermission):
                permission_code = "user.delete"

            return [Permission()]

        return [IsAuthenticated()]

    def get_object(self, pk):

        return get_object_or_404(
            User.objects.prefetch_related(
                "role",
                "role__permissions"
            ).select_related(
                "company"
            ),
            pk=pk
        )

    def get(self, request, pk):

        user = self.get_object(pk)

        serializer = UserSerializer(user)

        return Response(serializer.data)

    def put(self, request, pk):

        user = self.get_object(pk)

        serializer = UserCreateUpdateSerializer(
            user,
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            UserSerializer(user).data
        )

    def patch(self, request, pk):

        user = self.get_object(pk)

        serializer = UserCreateUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            UserSerializer(user).data
        )

    def delete(self, request, pk):

        user = self.get_object(pk)

        user.delete()

        return Response(
    {
        "detail": "Password changed successfully."
    },
    status=status.HTTP_200_OK,
)
    status=status.HTTP_204_NO_CONTENT

# ==========================================
# DASHBOARD
# ==========================================

class PlatformDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            # Platform Statistics
            "companies": Company.objects.count(),
            "organizations": OrgNode.objects.count(),
            "departments": Department.objects.count(),

            # User Statistics
            "users": User.objects.count(),
            "active_users": User.objects.filter(
                is_active=True
            ).count(),
            "inactive_users": User.objects.filter(
                is_active=False
            ).count(),

            # RBAC Statistics
            "roles": Role.objects.count(),
            "permissions": Permission.objects.count(),

            # System Status
            "system_status": "Healthy",
        }

        return Response(data)


# ==========================================
# ROLE VIEWSET
# ==========================================

class RoleViewSet(viewsets.ModelViewSet):

    serializer_class = RoleSerializer

    queryset = Role.objects.prefetch_related(
        "permissions"
    ).order_by(
        "role_name"
    )

    def get_permissions(self):

        if self.action in ["list", "retrieve"]:

            class Permission(HasRolePermission):
                permission_code = "role.view"

            return [Permission()]

        elif self.action == "create":

            class Permission(HasRolePermission):
                permission_code = "role.create"

            return [Permission()]

        elif self.action in ["update", "partial_update"]:

            class Permission(HasRolePermission):
                permission_code = "role.edit"

            return [Permission()]

        elif self.action == "destroy":

            class Permission(HasRolePermission):
                permission_code = "role.delete"

            return [Permission()]

        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        role = serializer.save()

        return Response(
            {
                "message": "Role created successfully.",
                "data": RoleSerializer(role).data
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop(
            "partial",
            False
        )

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(
            raise_exception=True
        )

        role = serializer.save()

        return Response({
            "message": "Role updated successfully.",
            "data": RoleSerializer(role).data
        })

    def destroy(self, request, *args, **kwargs):

        role = self.get_object()

        role.delete()

        return Response(
            {
                "message": "Role deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )


# ==========================================
# PERMISSION VIEWSET
# ==========================================

class PermissionViewSet(viewsets.ModelViewSet):

    serializer_class = PermissionSerializer

    queryset = Permission.objects.order_by(
        "display_order",
        "name"
    )

    def get_permissions(self):

        if self.action in ["list", "retrieve"]:

            class Permission(HasRolePermission):
                permission_code = "permission.view"

            return [Permission()]

        elif self.action == "create":

            class Permission(HasRolePermission):
                permission_code = "permission.create"

            return [Permission()]

        elif self.action in ["update", "partial_update"]:

            class Permission(HasRolePermission):
                permission_code = "permission.edit"

            return [Permission()]

        elif self.action == "destroy":

            class Permission(HasRolePermission):
                permission_code = "permission.delete"

            return [Permission()]

        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        permission = serializer.save()

        return Response(
            {
                "message": "Permission created successfully.",
                "data": PermissionSerializer(permission).data
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop(
            "partial",
            False
        )

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(
            raise_exception=True
        )

        permission = serializer.save()

        return Response({
            "message": "Permission updated successfully.",
            "data": PermissionSerializer(permission).data
        })

    def destroy(self, request, *args, **kwargs):

        permission = self.get_object()

        permission.delete()

        return Response(
            {
                "message": "Permission deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )


