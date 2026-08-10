from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CityViewSet,
    CompanyViewSet,
    CountryViewSet,
    DepartmentViewSet,
    StateViewSet,
    
)


app_name = 'companies'

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'states', StateViewSet, basename='state')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('', include(router.urls)),
    path('profile/', CompanyViewSet.as_view({'get': 'profile', 'patch': 'profile'}), name='company-profile'),
]
