M7 — Frameworks and Mapping

Document Status

Item

Details

Module

M7 — Frameworks and Mapping

Status

Implemented

Test Status

70 / 70 tests passing

Primary API Prefix

/api/frameworks/

Canonical Datapoint Owner

M4 — Datapoint Catalog

Framework Structure Owner

M7

Future Reporting Consumer

M8 / Future Reporting Modules

1. Overview

The M7 Frameworks and Mapping module provides the backend foundation for managing:

Reporting frameworks

Framework versions

Hierarchical framework nodes

Framework tree metadata

Framework-to-canonical-datapoint mappings

Mapping metadata and validation

Framework search and filtering

Framework tree retrieval

Datapoint mapping APIs

M7 owns the framework structure and mapping relationship.

M4 remains the source of truth for canonical datapoints.

The architectural relationship is:

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
M4 Datapoint

M7 does not duplicate or redefine the M4 Datapoint model.

2. Module Responsibilities

M7 is responsible for

Framework identity

Framework version management

Framework hierarchy/tree representation

Framework node metadata

Node hierarchy validation

Node depth and path calculation

Deterministic node ordering

Framework tree retrieval

Framework search and filtering

Framework-to-datapoint mapping

Mapping metadata

Mapping validation

Mapping filtering

RBAC integration through existing project infrastructure

Representative framework seed/import data

Automated tests

M7 does not implement

M4 datapoint definitions

Company answer storage

Report runs

Report versions

Disclosure assignment

Narrative answer workflows

Report PDF generation

Report Excel generation

Calculation execution

Auditor workflows

Materiality assessment logic

3. Architectural Boundary

The platform separates canonical data definitions from framework requirements.

M4
Canonical Datapoint Catalog
        |
        | canonical datapoints
        v
M7
Frameworks + Versions + Nodes + Mappings
        |
        | framework requirements
        v
Future Reporting Modules / M8
Report Runs + Answers + Reporting Output

The central architectural principle is:

M4 owns the canonical datapoint definition. M7 owns the framework structure and the relationship between framework nodes and canonical datapoints.

This supports the platform's:

Collect Once, Report Many

architecture.

4. Core M7 Models

M7 contains four primary models:

Framework
    |
    +-- FrameworkVersion
            |
            +-- FrameworkNode
                    |
                    +-- DatapointMapping
                            |
                            +-- M4 Datapoint

5. Framework

Framework represents the identity of an external reporting framework or standard.

Examples:

GRI

BRSR

GHG Protocol

ISSB

Fields

id
code
name
description
is_enabled
created_at
updated_at

Code

code is the stable machine-readable framework identifier.

Example:

GRI
BRSR
ISSB

Framework codes are unique.

Name

Human-readable framework name.

Description

Optional framework description.

Enabled State

is_enabled controls whether the framework is enabled for use.

Ordering

Frameworks are ordered by:

code

6. FrameworkVersion

FrameworkVersion represents a specific edition or version of a framework.

Framework
    |
    +-- FrameworkVersion
    +-- FrameworkVersion
    +-- FrameworkVersion

Fields

id
framework
version_code
version_name
effective_from
effective_to
published_at
is_active
is_default
created_at
updated_at

Version Identity

The combination:

framework + version_code

must be unique.

Default Version

Only one default version is allowed per framework.

Active Version Identity

Once a version is active, its framework and version code are treated as stable identity fields. The serializer prevents changing either value on an active version.

Ordering

Versions are ordered by:

framework.code
version_code

7. FrameworkNode

FrameworkNode represents an individual element in a framework hierarchy.

Every node belongs to exactly one FrameworkVersion.

A node can optionally reference another FrameworkNode as its parent.

Fields

id
framework_version
parent
code
title
description
instructions
node_type
display_order
depth
path
response_format
is_answerable
is_core
is_active
created_at
updated_at

depth and path are maintained as tree metadata.

8. Framework Node Types

The currently implemented node types are:

SECTION
SUBSECTION
DISCLOSURE
INDICATOR
SUBINDICATOR

SECTION

Major framework-level grouping.

SUBSECTION

Subdivision inside a section.

DISCLOSURE

A reporting/disclosure-level requirement.

INDICATOR

A more granular framework reporting indicator.

SUBINDICATOR

A further subdivision of an indicator.

The node type describes the structural role of the framework node. It does not define an M4 datapoint.

9. Framework Tree

The framework hierarchy is represented using the self-referencing parent relationship.

Representative structure:

GRI 2021
|
+-- TOPIC-STANDARDS
    |
    +-- GRI-300
        |
        +-- GRI-302
            |
            +-- 302-1
            |
            +-- 302-2

The database stores the parent-child relationship.

The model additionally stores materialized tree metadata:

depth
path

10. Tree Metadata

Depth

Root nodes have:

depth = 0

Each child has:

depth = parent.depth + 1

Example:

ROOT
depth = 0

CHILD
depth = 1

GRANDCHILD
depth = 2

Path

Example:

/ROOT/
/ROOT/CHILD/
/ROOT/CHILD/GRANDCHILD/

The path is calculated automatically when a node is saved.

11. Framework Node Validation

The current implementation enforces the following hierarchy rules.

11.1 Same-Version Parent

A node's parent must belong to the same framework version.

Invalid:

GRI 2021
|
+-- Node A
      |
      +-- Parent from GRI 2022

The operation is rejected.

11.2 Self-Parent Prevention

A node cannot be its own parent.

Node A
   |
   +-- parent = Node A

The operation is rejected.

11.3 Cycle Prevention

A node cannot be moved below one of its descendants.

Invalid:

A
|
+-- B
    |
    +-- C

Attempting to make A a child of C is rejected.

11.4 Node-Code Uniqueness

The combination:

framework_version + code

must be unique.

The same code may exist in different framework versions.

12. Node Save and Subtree Rebuild

When a FrameworkNode is saved:

Validation is performed.

Parent/child hierarchy rules are validated.

depth is recalculated.

path is recalculated.

The node is saved.

Descendant nodes are recursively updated.

Descendant depth/path metadata is rebuilt.

Therefore, moving a node also updates its descendant metadata.

Example:

Before:

ROOT-A
└── CHILD
    └── GRANDCHILD

After moving CHILD:

ROOT-B
└── CHILD
    └── GRANDCHILD

Result:

CHILD
depth = 1
path = /ROOT-B/CHILD/

GRANDCHILD
depth = 2
path = /ROOT-B/CHILD/GRANDCHILD/

13. DatapointMapping

DatapointMapping connects a framework node to a canonical M4 datapoint.

FrameworkNode
      |
      v
DatapointMapping
      |
      v
M4 Datapoint

A framework node may have multiple mappings.

The same canonical datapoint can be reused by different framework nodes where appropriate.

This supports the platform's "Collect Once, Report Many" architecture.

14. M4 Datapoint Ownership

M7 does not create a second datapoint model.

The canonical datapoint remains owned by M4.

The relationship is:

M4 Datapoint
      |
      v
DatapointMapping
      |
      v
FrameworkNode

M4 remains the source of truth for datapoint-specific information such as:

code

label

data type

category

module

collection level

frequency

M7 stores the mapping relationship and mapping metadata.

15. Mapping Types

The current implementation supports:

DIRECT
NARRATIVE
CALCULATED

DIRECT

The framework node directly corresponds to a canonical datapoint.

NARRATIVE

The framework requirement represents a narrative/manual requirement.

M7 stores mapping metadata but does not implement the future narrative answer workflow.

CALCULATED

The framework node depends on a calculated or derived value.

M7 stores mapping metadata only. Calculation execution belongs to a future calculation/reporting layer.

16. Mapping Aggregation

The current aggregation options are:

NONE
SUM
AVG
LATEST
COUNT

Validation

A DIRECT mapping must use:

aggregation = NONE

A NARRATIVE mapping must also use:

aggregation = NONE

Therefore:

DIRECT + SUM

is invalid.

And:

NARRATIVE + AVG

is invalid.

17. Mapping Metadata

The mapping model contains:

id
framework_node
datapoint
mapping_type
aggregation
transform_expression
is_primary
confidence
mapping_note
reviewed_at
created_at
updated_at

Transform Expression

transform_expression stores optional transformation metadata.

M7 does not execute arbitrary transformation expressions.

Primary Mapping

is_primary identifies the primary mapping for a framework node.

Only one primary mapping is allowed per framework node.

Confidence

The current confidence values are:

CONFIRMED
PROVISIONAL

Mapping Note

Stores additional mapping context or review notes.

Reviewed At

Optional timestamp indicating when the mapping was reviewed.

18. Mapping Validation

The current implementation enforces:

Active Framework Node

Only active framework nodes can have mappings.

framework_node.is_active = true

Active M4 Datapoint

Only active M4 datapoints can be mapped.

datapoint.is_active = true

Duplicate Mapping Prevention

The combination:

framework_node + datapoint

must be unique.

Primary Mapping

Only one mapping per node can have:

is_primary = true

19. API Overview

All M7 APIs are registered under:

/api/frameworks/

Current API groups:

/api/frameworks/
/api/frameworks/versions/
/api/frameworks/nodes/
/api/frameworks/mappings/
/api/frameworks/versions/<version_id>/tree/

20. Framework API

List

GET /api/frameworks/

Create

POST /api/frameworks/

Example:

{
    "code": "GRI",
    "name": "Global Reporting Initiative",
    "description": "GRI Standards",
    "is_enabled": true
}

Detail

GET /api/frameworks/<framework_id>/

Update

PUT /api/frameworks/<framework_id>/

Partial Update

PATCH /api/frameworks/<framework_id>/

Delete

DELETE /api/frameworks/<framework_id>/

21. Framework Filters

Search

Searches framework code and name.

GET /api/frameworks/?search=GRI

Enabled State

GET /api/frameworks/?is_enabled=true

or:

GET /api/frameworks/?is_enabled=false

22. Framework Version API

Framework versions use non-nested routes.

List

GET /api/frameworks/versions/

Create

POST /api/frameworks/versions/

Detail

GET /api/frameworks/versions/<version_id>/

Update

PUT /api/frameworks/versions/<version_id>/

Partial Update

PATCH /api/frameworks/versions/<version_id>/

Delete

DELETE /api/frameworks/versions/<version_id>/

The current implementation does not use:

/api/frameworks/<framework_id>/versions/

for version routing.

23. Framework Version Filters

Framework

GET /api/frameworks/versions/?framework=<framework_id>

Active State

GET /api/frameworks/versions/?is_active=true

Default State

GET /api/frameworks/versions/?is_default=true

Search

Searches:

version_code
version_name

Example:

GET /api/frameworks/versions/?search=2021

Filters can be combined.

24. Framework Node API

List

GET /api/frameworks/nodes/

Create

POST /api/frameworks/nodes/

Detail

GET /api/frameworks/nodes/<node_id>/

Update

PUT /api/frameworks/nodes/<node_id>/

Partial Update

PATCH /api/frameworks/nodes/<node_id>/

Delete

DELETE /api/frameworks/nodes/<node_id>/

25. Framework Node Filters

Framework Version

GET /api/frameworks/nodes/?framework_version=<version_id>

Code

GET /api/frameworks/nodes/?code=302

The code filter performs case-insensitive partial matching.

Node Type

GET /api/frameworks/nodes/?node_type=DISCLOSURE

Active State

GET /api/frameworks/nodes/?is_active=true

Filters can be combined.

Example:

GET /api/frameworks/nodes/?framework_version=<id>&node_type=DISCLOSURE&is_active=true

26. Complete Framework Tree API

GET /api/frameworks/versions/<version_id>/tree/

The endpoint returns:

Framework information

Framework version information

Complete nested active-node hierarchy

Example:

{
    "framework": {
        "id": "...",
        "code": "GRI",
        "name": "Global Reporting Initiative"
    },
    "version": {
        "id": "...",
        "code": "2021",
        "name": "GRI Standards 2021"
    },
    "tree": [
        {
            "id": "...",
            "code": "TOPIC-STANDARDS",
            "title": "Topic Standards",
            "node_type": "SECTION",
            "display_order": 1,
            "depth": 0,
            "path": "/TOPIC-STANDARDS/",
            "is_answerable": false,
            "is_core": true,
            "is_active": true,
            "children": []
        }
    ]
}

Only active nodes are returned.

Sibling nodes are ordered deterministically using:

display_order
code

27. Datapoint Mapping API

List

GET /api/frameworks/mappings/

Create

POST /api/frameworks/mappings/

Detail

GET /api/frameworks/mappings/<mapping_id>/

Update

PUT /api/frameworks/mappings/<mapping_id>/

Partial Update

PATCH /api/frameworks/mappings/<mapping_id>/

Delete

DELETE /api/frameworks/mappings/<mapping_id>/

28. Mapping Create Example

POST /api/frameworks/mappings/

Example:

{
    "framework_node": "<framework-node-id>",
    "datapoint": "<m4-datapoint-id>",
    "mapping_type": "DIRECT",
    "aggregation": "NONE",
    "is_primary": true,
    "confidence": "CONFIRMED",
    "mapping_note": "Primary framework mapping."
}

29. Mapping Serializer Response

The serializer exposes:

id

framework_node
framework_node_code

framework_version_id
framework_version_code

datapoint
datapoint_code
datapoint_label
datapoint_data_type

mapping_type
aggregation
transform_expression
is_primary
confidence
mapping_note
reviewed_at

created_at
updated_at

The following fields are read-only:

framework_node_code
framework_version_id
framework_version_code
datapoint_code
datapoint_label
datapoint_data_type
created_at
updated_at

The frontend should submit IDs for:

framework_node
datapoint

and use the related descriptive fields returned by the API.

30. Mapping Filters

Framework Node

GET /api/frameworks/mappings/?framework_node=<node_id>

Framework Version

GET /api/frameworks/mappings/?framework_version=<version_id>

Datapoint

GET /api/frameworks/mappings/?datapoint=<datapoint_id>

Mapping Type

GET /api/frameworks/mappings/?mapping_type=DIRECT

GET /api/frameworks/mappings/?mapping_type=NARRATIVE

GET /api/frameworks/mappings/?mapping_type=CALCULATED

Confidence

GET /api/frameworks/mappings/?confidence=CONFIRMED

GET /api/frameworks/mappings/?confidence=PROVISIONAL

Primary State

GET /api/frameworks/mappings/?is_primary=true

or:

GET /api/frameworks/mappings/?is_primary=false

Filters can be combined.

Example:

GET /api/frameworks/mappings/?framework_version=<id>&mapping_type=DIRECT&is_primary=true

31. Authentication and RBAC

M7 uses the existing project-wide authentication and RBAC infrastructure.

Framework, version, node, and mapping CRUD APIs use:

RBACModelViewSet

The framework tree endpoint uses:

IsAuthenticated
HasRolePermission

The tree endpoint requires:

framework_node.view

The M7 viewsets use these module codes:

framework
framework_version
framework_node
framework_mapping

M7 does not implement a separate authentication or authorization system.

32. Serializer Validation

FrameworkVersion

An active framework version cannot change:

framework
version_code

FrameworkNode

The serializer rejects:

self-parenting
parent from a different framework version

DatapointMapping

The serializer rejects:

inactive framework node
inactive datapoint
DIRECT + aggregation
NARRATIVE + aggregation

33. Read-Only Fields

Framework

created_at
updated_at

FrameworkVersion

created_at
updated_at
framework_code

FrameworkNode

depth
path
created_at
updated_at
parent_code

DatapointMapping

framework_node_code
framework_version_id
framework_version_code
datapoint_code
datapoint_label
datapoint_data_type
created_at
updated_at

34. Seed / Import Strategy

M7 may contain representative framework content to demonstrate:

framework creation;

framework versioning;

multi-level hierarchy;

framework node relationships;

canonical datapoint mappings.

Representative content is not intended to be a complete population of GRI, BRSR, ISSB, or other standards.

Official framework content should be populated using controlled and reviewed source material.

If enabled in the project:

python manage.py seed_frameworks

The seed should be idempotent, meaning repeated execution should not create duplicate framework, version, or node records.

35. Testing

The M7 test suite covers the implemented model, serializer, API, tree, validation, mapping, and filtering behavior.

Current Test Status

70 tests
70 passed
0 failed

Run all M7 tests

python manage.py test apps.frameworks

Run with detailed output

python manage.py test apps.frameworks -v 2

Model tests

python manage.py test apps.frameworks.test.test_models

Serializer tests

python manage.py test apps.frameworks.test.test_serializers

API/view tests

python manage.py test apps.frameworks.test.test_views

36. Test Coverage

The current test suite covers:

Framework

Framework creation

Framework uniqueness

Framework representation

Framework API listing

Framework detail

Framework API creation

Framework API update

Search

Enabled-state filtering

FrameworkVersion

Version creation

Version uniqueness

Default-version constraint

Framework filtering

Active-state filtering

Default-state filtering

Search

Active-version identity validation

FrameworkNode

Root node creation

Child node creation

Multi-level hierarchy

Depth calculation

Path calculation

Self-parent rejection

Same-version parent validation

Cycle prevention

Node-code uniqueness

Node movement

Descendant metadata rebuilding

Node filtering

Framework Tree

Tree retrieval

Framework metadata

Version metadata

Nested child serialization

Inactive-node exclusion

Invalid-version handling

Deterministic hierarchy

DatapointMapping

Mapping creation

Mapping retrieval

Duplicate mapping protection

Primary mapping protection

Active-node validation

Active-datapoint validation

Mapping-type validation

Aggregation validation

Mapping filtering

Related datapoint serializer output

37. Django Verification

Run:

python manage.py check

Then:

python manage.py makemigrations --check

Then:

python manage.py test apps.frameworks

Expected test result:

Ran 70 tests

OK

38. Representative Mapping Flow

M4 Datapoint Catalog
        |
        v
M4 Datapoint
        ^
        |
DatapointMapping
        ^
        |
FrameworkNode
        ^
        |
FrameworkVersion
        ^
        |
Framework

Example:

GRI
|
+-- GRI 2021
    |
    +-- GRI-300
        |
        +-- GRI-302
            |
            +-- 302-1
                |
                v
          DatapointMapping
                |
                v
          M4 Datapoint

39. Relationship to Future M8 Reporting

M7 provides the framework structure and mapping foundation for future reporting functionality.

Expected future flow:

Framework
    |
FrameworkVersion
    |
FrameworkNode
    |
DatapointMapping
    |
Canonical Datapoint
    |
Company Data / Answer Storage
    |
Report Run
    |
Disclosure Assignment / Resolution
    |
Report Output

M7 stops before report-run and answer-storage stages.

Future reporting modules can use M7 to determine:

which framework is selected;

which version is selected;

which framework nodes exist;

node hierarchy;

node ordering;

answerability;

associated canonical datapoints;

mapping type;

mapping metadata.

40. Future Work Outside M7

The following remain outside the current M7 boundary:

Complete Framework Population

Complete reviewed population of GRI, BRSR, ISSB, and other frameworks.

Mapping Review

Domain review and validation of framework-to-datapoint mappings.

Answer Storage

A future module will own company responses.

Narrative Workflow

Future functionality may support:

Draft
Submit
Review
Approve
Lock

Calculation Execution

A future calculation layer will execute formulas and derived datapoint logic.

Report Runs

A future M8 reporting module will manage reporting executions and report versions.

Report Generation

Future reporting functionality will generate:

PDF
Excel
Other reporting outputs

Auditor Workflows

Auditor-specific access, review, and approval workflows remain outside M7.

41. M7 Completion Boundary

The current M7 foundation is considered implemented when:

Frameworks can be created and retrieved.

Framework versions can be created and retrieved.

Active framework version identity is protected.

Framework nodes support multi-level hierarchies.

Parent-child relationships are validated.

Self-parenting is prevented.

Cyclic relationships are prevented.

Node-code uniqueness is enforced per framework version.

Node depth is calculated automatically.

Node path is calculated automatically.

Descendant metadata is rebuilt after node movement.

Tree ordering is deterministic.

Complete active framework trees can be retrieved through one API request.

M7 references the canonical M4 datapoint model.

Duplicate node/datapoint mappings are prevented.

Only active nodes can receive mappings.

Only active datapoints can be mapped.

Mapping types and aggregation rules are validated.

Only one primary mapping can exist per node.

Framework, version, node, and mapping APIs are available.

API filtering is available.

Existing project RBAC is integrated.

Automated M7 tests pass.

Django system checks can be executed.

M7 remains independent of future M8 reporting functionality.

42. Final Architecture

                         ESG Platform
                              |
              +---------------+---------------+
              |                               |
             M4                              M7
              |                               |
              v                               v
    Canonical Datapoints             Framework Catalog
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
                                        M4 Datapoint
                                              |
                                              v
                                      Future M8
                                              |
                               +--------------+--------------+
                               |                             |
                          Report Runs                    Answers
                               |
                               v
                         Report Output

43. Final Model Summary

Framework
│
├── code
├── name
├── description
└── is_enabled
      │
      └── FrameworkVersion
            │
            ├── version_code
            ├── version_name
            ├── effective_from
            ├── effective_to
            ├── published_at
            ├── is_active
            └── is_default
                  │
                  └── FrameworkNode
                        │
                        ├── code
                        ├── title
                        ├── description
                        ├── instructions
                        ├── node_type
                        ├── display_order
                        ├── depth
                        ├── path
                        ├── response_format
                        ├── is_answerable
                        ├── is_core
                        └── is_active
                              │
                              └── DatapointMapping
                                    │
                                    ├── mapping_type
                                    ├── aggregation
                                    ├── transform_expression
                                    ├── is_primary
                                    ├── confidence
                                    ├── mapping_note
                                    └── reviewed_at
                                          │
                                          v
                                    M4 Datapoint

44. Final Status

M7 currently provides the framework catalog and framework-to-datapoint mapping foundation for the ESG platform.

Current implementation:

Framework
        ✓

FrameworkVersion
        ✓

FrameworkNode
        ✓

Hierarchy validation
        ✓

Self-parent prevention
        ✓

Cycle prevention
        ✓

Depth/path metadata
        ✓

Tree API
        ✓

DatapointMapping
        ✓

Mapping validation
        ✓

Mapping filters
        ✓

Framework/version/node APIs
        ✓

RBAC integration
        ✓

Automated tests
        ✓ 70/70 passing

Final architectural boundary:

M4 = What data is collected
M7 = Where that data participates in a framework
M8 = How that framework is used for reporting

M7 therefore provides a stable, versioned, validated framework and mapping foundation while keeping canonical datapoint ownership in M4 and future reporting execution in M8.