from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReportingPeriodViewSet


app_name = "periods"

router = DefaultRouter()
router.register(r"", ReportingPeriodViewSet, basename="reporting-period")

urlpatterns = [
    path("", include(router.urls)),
]
