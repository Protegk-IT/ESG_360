from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CityViewSet,
    CompanyViewSet,
    CountryViewSet,
    DepartmentViewSet,
    StateViewSet,
    UserDepartmentViewSet,
)


app_name = 'companies'

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'states', StateViewSet, basename='state')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'user-departments', UserDepartmentViewSet, basename='user-department')

urlpatterns = [
    path('', include(router.urls)),
]
