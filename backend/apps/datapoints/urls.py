from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    UnitFamilyViewSet,
    UnitViewSet,
    DatapointCategoryViewSet,
    DatapointViewSet,
    DatapointOptionViewSet,
    DatapointTableColumnViewSet,
    DatapointTableRowViewSet,
)

router = DefaultRouter()

router.register(r"unit-families", UnitFamilyViewSet, basename="unit-family")
router.register(r"units", UnitViewSet, basename="unit")
router.register(r"categories", DatapointCategoryViewSet, basename="datapoint-category")
router.register(r"options", DatapointOptionViewSet, basename="datapoint-option")
router.register(r"table-columns",DatapointTableColumnViewSet,basename="datapoint-table-column",)
router.register(r"table-rows",DatapointTableRowViewSet,basename="datapoint-table-row",)
router.register(r"", DatapointViewSet, basename="datapoint")

urlpatterns = [
    path("", include(router.urls)),
]