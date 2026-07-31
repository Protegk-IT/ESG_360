from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    LogoutView,
    MeView,
    PlatformDashboardView,
    UserListCreateView,
    UserDetailView,
    RoleViewSet,
    PermissionViewSet,
    UserRoleScopeViewSet
)

router = DefaultRouter()
router.register("roles", RoleViewSet, basename="roles")
router.register("permissions", PermissionViewSet, basename="permissions")
router.register("user-role-scopes",UserRoleScopeViewSet,basename="user-role-scope")
urlpatterns = [
    # Authentication
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),

    # Dashboard
    path("dashboard/", PlatformDashboardView.as_view()),

    # Users
    path("users/", UserListCreateView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view()),

    # Role & Permission
    path("", include(router.urls)),
]

