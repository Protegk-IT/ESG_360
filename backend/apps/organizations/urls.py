from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrgNodeViewSet


app_name = "organizations"

router = DefaultRouter()
router.register(r"nodes", OrgNodeViewSet, basename="org-node")

urlpatterns = [
    path("", include(router.urls)),
    path("tree/",OrgNodeViewSet.as_view({"get": "tree"}),name="org-tree"),
]
