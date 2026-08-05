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
    # Authentication
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", CurrentUserView.as_view()),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
    ),

    # CRUD APIs
    path("", include(router.urls)),
]