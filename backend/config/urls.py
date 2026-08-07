"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts.views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    ChangePasswordView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("api/auth/me/", CurrentUserView.as_view(), name="me"),

    path('api/accounts/', include('apps.accounts.urls')),
    path("api/", include("apps.core.urls")),
    path('api/company/', include('apps.companies.urls')),
    path("api/org/", include("apps.organizations.urls")),
    path("api/periods/", include("apps.periods.urls"))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
