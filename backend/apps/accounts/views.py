from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,viewsets
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import LoginSerializer,RoleSerializer,PermissionSerializer
from .models import User,Permissions,Role
from .serializers import (
    UserSerializer,
    UserCreateUpdateSerializer
)

class UserListCreateView(APIView):

    def get(self, request):
        users = User.objects.select_related(
            "department",
            "company",
            "role"
        ).prefetch_related(
            "assigned_plants"
        )

        serializer = UserSerializer(users, many=True)

        return Response(serializer.data)


    def post(self, request):

        serializer = UserCreateUpdateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )

class UserDetailView(APIView):

    def get_object(self, pk):
        return get_object_or_404(
            User.objects.select_related(
                "department",
                "company",
                "role"
            ).prefetch_related(
                "assigned_plants"
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

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(UserSerializer(user).data)


    def patch(self, request, pk):

        user = self.get_object(pk)

        serializer = UserCreateUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(UserSerializer(user).data)


    def delete(self, request, pk):

        user = self.get_object(pk)

        user.delete()

        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

class MeView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "employee_code": user.employee_code,
            "designation": user.designation,
            "mobile_number": user.mobile_number,
            "profile_image": (
                request.build_absolute_uri(user.profile_image.url)
                if user.profile_image
                else None
            ),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        })


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
            password=password,
        )
        print("Username:", username)
        print("Authenticated User:", user)

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

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "csrf_token": csrf_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                    "is_staff": user.is_staff,
                }
            },
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        logout(request)

        return Response(
            {
                "success": True,
                "message": "Logout successful."
            },
            status=status.HTTP_200_OK
        )

class PlatformDashboardView(APIView):

    def get(self, request):

        return Response(
            {
                # "companies": Company.objects.count(),
                "users": User.objects.count(),
                "platform_admins": User.objects.filter(
                    is_superuser=True
                ).count(),
                "system_status": "Healthy",
            }
        )
class RoleViewSet(viewsets.ModelViewSet):

    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    queryset = Role.objects.prefetch_related(
        "permissions"
    ).order_by("role_name")

    def get_queryset(self):

        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            queryset = queryset.exclude(
                role_code="SUPERADMIN"
            )

        return queryset

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        role = serializer.save()

        return Response(
            {
                "message": "Role created successfully.",
                "data": RoleSerializer(role).data
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)

        role = serializer.save()

        return Response(
            {
                "message": "Role updated successfully.",
                "data": RoleSerializer(role).data
            }
        )

    def destroy(self, request, *args, **kwargs):

        role = self.get_object()

        role.delete()

        return Response(
            {
                "message": "Role deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

class PermissionViewSet(viewsets.ModelViewSet):

    serializer_class = PermissionSerializer

    permission_classes = [IsAuthenticated]

    queryset = Permissions.objects.order_by(
        "display_order",
        "name"
    )
