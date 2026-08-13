from rest_framework.routers import DefaultRouter
from .views import ModuleViewSet

router = DefaultRouter()
router.register(r"", ModuleViewSet, basename="module")

urlpatterns = router.urls