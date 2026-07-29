from django.urls import path
from .views import (
    UserListCreateView,
    UserDetailView,
    MeView,
    LoginView,
    LogoutView,
)

urlpatterns = [
    path("users/", UserListCreateView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view()),
    path("me/", MeView.as_view()),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]