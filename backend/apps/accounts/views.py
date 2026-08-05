from urllib import request

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
            UserSerializer(user).data,
            status=status.HTTP_200_OK,
        )


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
            {
                "detail": "Password changed successfully."
            },
            status=status.HTTP_200_OK,
        )