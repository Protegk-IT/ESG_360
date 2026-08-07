from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    LogoutView,
    CurrentUserView,
    ChangePasswordView,
    UserViewSet,
    RoleViewSet,
    PermissionViewSet,
    CSRFTokenView,
)

router = DefaultRouter()

router.register(
    "users",
    UserViewSet,
    basename="users",
)

router.register(
    "roles",
    RoleViewSet,
    basename="roles",
)

router.register(
    "permissions",
    PermissionViewSet,
    basename="permissions",
)

urlpatterns = [
    
    path("csrf/", CSRFTokenView.as_view(), name="csrf-token"),

    # CRUD APIs
    path("", include(router.urls)),
]