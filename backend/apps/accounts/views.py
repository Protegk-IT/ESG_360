from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from .permissions import HasRolePermission
from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import User,Role, Permissions, User,UserRoleScope
from .serializers import (
    LoginSerializer,
    UserSerializer,
    UserCreateUpdateSerializer,
    UserRoleScopeSerializer,
    RoleSerializer,
    PermissionSerializer,
)

# ==========================================
# LOGIN
# ==========================================

class LoginView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {
                    "success": False,
                    "message": "Invalid username or password."
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        login(request, user)

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
            }
        })


# ==========================================
# LOGOUT
# ==========================================

class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        logout(request)

        return Response({
            "success": True,
            "message": "Logout successful."
        })


# ==========================================
# ME
# ==========================================

class MeView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = UserSerializer(request.user)

        return Response(serializer.data)


# ==========================================
# USER LIST / CREATE
# ==========================================

class UserListCreateView(APIView):

    def get_permissions(self):

        if self.request.method == "GET":

            class Permission(HasRolePermission):
                permission_code = "user.view"

            return [Permission()]

        elif self.request.method == "POST":

            class Permission(HasRolePermission):
                permission_code = "user.create"

            return [Permission()]

        return [IsAuthenticated()]

    def get(self, request):

        users = User.objects.prefetch_related(
            "role",
            "role__permissions"
        ).select_related(
            "company"
        )

        serializer = UserSerializer(
            users,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = UserCreateUpdateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.save()

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
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
            data=request.data
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
            partial=True
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
                "message": "User deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )


# ==========================================
# DASHBOARD
# ==========================================

class PlatformDashboardView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        return Response({
            "total_users": User.objects.count(),
            "total_roles": Role.objects.count(),
            "total_permissions": Permissions.objects.count(),
            "active_users": User.objects.filter(
                is_active=True
            ).count(),
            "system_status": "Healthy"
        })


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

    queryset = Permissions.objects.order_by(
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


class UserRoleScopeViewSet(viewsets.ModelViewSet):

    queryset = UserRoleScope.objects.all()

    serializer_class = UserRoleScopeSerializer

    permission_classes = [
        IsAuthenticated
    ]
