from django.urls import path

from .views import (
    FrameworkDetailView,
    FrameworkListCreateView,
    FrameworkNodeDetailView,
    FrameworkVersionDetailView,
    FrameworkVersionListView,
    FrameworkVersionTreeView,
    DatapointMappingListCreateView,
    DatapointMappingDetailView,
)


app_name = "frameworks"


urlpatterns = [

    # Frameworks

    path(
        "",
        FrameworkListCreateView.as_view(),
        name="framework-list-create",
    ),

    path(
        "<uuid:pk>/",
        FrameworkDetailView.as_view(),
        name="framework-detail",
    ),

    # Framework versions

    path(
        "<uuid:framework_id>/versions/",
        FrameworkVersionListView.as_view(),
        name="framework-version-list-create",
    ),

    path(
        "versions/<uuid:pk>/",
        FrameworkVersionDetailView.as_view(),
        name="framework-version-detail",
    ),

    # Framework tree

    path(
        "versions/<uuid:version_id>/tree/",
        FrameworkVersionTreeView.as_view(),
        name="framework-version-tree",
    ),

    # Framework nodes

    path(
        "nodes/<uuid:pk>/",
        FrameworkNodeDetailView.as_view(),
        name="framework-node-detail",
    ),


    path(
    "mappings/",
    DatapointMappingListCreateView.as_view(),
    name="mapping-list-create",
    ),

    path(
    "mappings/<uuid:pk>/",
    DatapointMappingDetailView.as_view(),
    name="mapping-detail",
    ),
]






'''
Your resulting endpoints

Because we will register this under:

/api/frameworks/

you'll get:

GET     /api/frameworks/
POST    /api/frameworks/


GET     /api/frameworks/<framework_id>/


GET     /api/frameworks/<framework_id>/versions/
POST    /api/frameworks/<framework_id>/versions/


GET     /api/frameworks/versions/<version_id>/
PUT     /api/frameworks/versions/<version_id>/
PATCH   /api/frameworks/versions/<version_id>/


GET     /api/frameworks/versions/<version_id>/tree/


GET     /api/frameworks/nodes/<node_id>/
'''
