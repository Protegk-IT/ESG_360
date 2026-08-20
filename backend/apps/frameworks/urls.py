from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FrameworkViewSet,
    FrameworkVersionViewSet,
    FrameworkNodeViewSet,
    FrameworkTreeView,
    DatapointMappingViewSet,
)


app_name = "frameworks"


router = DefaultRouter()

# IMPORTANT:
# Register specific/static prefixes BEFORE the empty prefix.

router.register(
    r"versions",
    FrameworkVersionViewSet,
    basename="framework-version",
)

router.register(
    r"nodes",
    FrameworkNodeViewSet,
    basename="framework-node",
)

router.register(
    r"mappings",
    DatapointMappingViewSet,
    basename="mapping",
)

router.register(
    r"",
    FrameworkViewSet,
    basename="framework",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),

    path(
        "versions/<uuid:version_id>/tree/",
        FrameworkTreeView.as_view(),
        name="framework-tree",
    ),
]
