from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApprovedAnswerCalculationAPIView,
    CalculationPreviewAPIView,
    CalculationResultCreateAPIView,
    CalculationResultViewSet,
    CalculationRuleViewSet,
    EmissionFactorSourceViewSet,
    EmissionFactorViewSet,
)
app_name = "calculations"

router = DefaultRouter()

router.register(r"factor-sources",EmissionFactorSourceViewSet,basename="factor-source",)
router.register(r"factors",EmissionFactorViewSet,basename="factor",)
router.register(r"rules",CalculationRuleViewSet,basename="calculation-rule",)
router.register(r"results",CalculationResultViewSet,basename="calculation-result",)


urlpatterns = [
    path("",include(router.urls),),
    path("preview/",CalculationPreviewAPIView.as_view(),name="calculation-preview",),
    path("approved-answer/",ApprovedAnswerCalculationAPIView.as_view(),name="approved-answer-calculate",),
    path("results/create/",CalculationResultCreateAPIView.as_view(),name="calculation-result-create",),
]