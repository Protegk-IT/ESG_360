from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import (
    UserListCreateView,
    UserDetailView,
    MeView,
    LoginView,
    LogoutView, RoleViewSet, PermissionViewSet  
)

app_name = 'accounts'
router = DefaultRouter()

router.register(r"roles",RoleViewSet,basename="roles")

router.register(r"permissions",PermissionViewSet,basename="permissions")

urlpatterns = [
    path("users/", UserListCreateView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view()),
    path("me/", MeView.as_view()),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", include(router.urls)),
]