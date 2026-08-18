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
===========================================================
M7 FRAMEWORKS AND MAPPING API ENDPOINTS
===========================================================

Registered under:

/api/frameworks/


-----------------------------------------------------------
1. FRAMEWORKS
-----------------------------------------------------------

GET
/api/frameworks/

List all frameworks.

POST
/api/frameworks/

Create a framework.


GET
/api/frameworks/<framework_id>/

Retrieve a framework.

PUT
/api/frameworks/<framework_id>/

Update a framework.

PATCH
/api/frameworks/<framework_id>/

Partially update a framework.


-----------------------------------------------------------
2. FRAMEWORK VERSIONS
-----------------------------------------------------------

GET
/api/frameworks/<framework_id>/versions/

List versions belonging to a framework.

POST
/api/frameworks/<framework_id>/versions/

Create a new framework version.


GET
/api/frameworks/versions/<version_id>/

Retrieve a framework version.

PUT
/api/frameworks/versions/<version_id>/

Update a framework version.

PATCH
/api/frameworks/versions/<version_id>/

Partially update a framework version.


-----------------------------------------------------------
3. FRAMEWORK TREE
-----------------------------------------------------------

GET
/api/frameworks/versions/<version_id>/tree/

Retrieve the complete framework hierarchy
in a single API request.

Example:

Framework
    |
    └── FrameworkVersion
            |
            ├── Section
            │     └── Subsection
            │            └── Disclosure
            |
            └── Section
                  └── Disclosure


-----------------------------------------------------------
4. FRAMEWORK NODE
-----------------------------------------------------------

GET
/api/frameworks/nodes/<node_id>/

Retrieve details of a specific framework node.


-----------------------------------------------------------
5. DATAPOINT MAPPINGS
-----------------------------------------------------------

GET
/api/frameworks/mappings/

List all framework-to-datapoint mappings.

POST
/api/frameworks/mappings/

Create a new framework-to-datapoint mapping.


GET
/api/frameworks/mappings/<mapping_id>/

Retrieve a specific datapoint mapping.

PUT
/api/frameworks/mappings/<mapping_id>/

Update a datapoint mapping.

PATCH
/api/frameworks/mappings/<mapping_id>/

Partially update a datapoint mapping.

DELETE
/api/frameworks/mappings/<mapping_id>/

Delete a datapoint mapping.


-----------------------------------------------------------
6. DATAPOINT MAPPING FILTERS
-----------------------------------------------------------

Filter mappings by framework node:

GET
/api/frameworks/mappings/?framework_node=<node_id>


Filter mappings by canonical M4 datapoint:

GET
/api/frameworks/mappings/?datapoint=<datapoint_id>


Filter mappings by mapping type:

GET
/api/frameworks/mappings/?mapping_type=DIRECT

GET
/api/frameworks/mappings/?mapping_type=NARRATIVE

GET
/api/frameworks/mappings/?mapping_type=CALCULATED


Filter mappings by confidence:

GET
/api/frameworks/mappings/?confidence=CONFIRMED

GET
/api/frameworks/mappings/?confidence=PROVISIONAL


Multiple filters can be combined:

GET
/api/frameworks/mappings/?framework_node=<node_id>&mapping_type=DIRECT


===========================================================
M7 CORE FLOW
===========================================================

Framework
    |
    v
FrameworkVersion
    |
    v
FrameworkNode
    |
    v
DatapointMapping
    |
    v
Canonical M4 Datapoint


The Framework app does NOT create or duplicate
the Datapoint model.

Datapoints are owned by the M4 Datapoint Catalog.


===========================================================
AUTHENTICATION
===========================================================

All M7 APIs use the project's global DRF authentication
and permission configuration.

Authentication:
SessionAuthentication

Permission:
IsAuthenticated

RBAC:
Not implemented yet.


===========================================================
'''