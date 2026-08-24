from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CalculationPreviewAPIView,
    CalculationRuleViewSet,
    EmissionFactorSourceViewSet,
    EmissionFactorViewSet,
)
app_name = "calculations"

router = DefaultRouter()

router.register(r"factor-sources",EmissionFactorSourceViewSet,basename="factor-source",)
router.register(r"factors",EmissionFactorViewSet,basename="factor",)
router.register(r"rules",CalculationRuleViewSet,basename="calculation-rule",)


urlpatterns = [
    path("",include(router.urls),),
    path("preview/",CalculationPreviewAPIView.as_view(),name="calculation-preview",),
]