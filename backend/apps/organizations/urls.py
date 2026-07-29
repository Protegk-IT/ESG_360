from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, FacilityViewSet, OrganizationViewSet


app_name = 'organizations'

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'facilities', FacilityViewSet, basename='facility')

urlpatterns = [
    path('', include(router.urls)),
]
