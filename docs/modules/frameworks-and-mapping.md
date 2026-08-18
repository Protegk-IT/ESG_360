# M7 — Frameworks and Mapping

## Overview

The M7 Frameworks and Mapping module provides the backend foundation for managing reporting frameworks, framework versions, hierarchical framework trees, and mappings between framework disclosures/nodes and the canonical datapoints defined by the M4 Datapoint Catalog.

M7 owns the framework structure and mapping relationship. M4 remains the source of truth for canonical datapoints.

The module intentionally does not implement report runs, disclosure assignment, answer storage, calculation execution, or report generation.

```text
Framework
    |
    +-- FrameworkVersion
            |
            +-- FrameworkNode
                    |
                    +-- DatapointMapping
                            |
                            +-- M4 Datapoint
```

---

## 1. Module Responsibilities

M7 is responsible for:

- Framework catalog identity
- Framework version management
- Framework hierarchy/tree representation
- Framework node metadata
- Deterministic tree ordering
- Framework hierarchy validation
- Framework-to-datapoint mapping metadata
- Mapping validation
- Framework tree retrieval APIs
- Datapoint mapping APIs
- Representative framework seed/import data

M7 does not implement:

- Report run/version models
- User disclosure assignment
- Company answer storage
- Narrative answer workflows
- Report PDF/Excel generation
- Calculation engines
- Auditor access
- Materiality assessment logic
- M4 datapoint definitions

---

## 2. Framework

`Framework` represents the identity of a reporting framework or standard.

Examples:

- GRI
- BRSR
- GHG Protocol
- ISSB

Core fields include:

```text
id
code
name
description
is_enabled
created_at
updated_at
```

`code` is the stable machine-readable framework identifier.

Framework codes are unique.

Framework identity must not be confused with the platform Module Registry. A module is a software capability; a framework is an external reporting standard/catalog.

---

## 3. FrameworkVersion

A framework can have multiple editions or versions.

```text
Framework
    |
    +-- FrameworkVersion
    +-- FrameworkVersion
    +-- FrameworkVersion
```

Core fields include:

```text
framework
version_code
version_name
effective_from
effective_to
published_at
is_active
is_default
```

The combination of `framework + version_code` is unique.

A version already used for reporting should be treated as a stable identity and should not be casually renamed or repurposed.

---

## 4. FrameworkNode

`FrameworkNode` represents an individual node in a framework hierarchy.

Every node belongs to exactly one `FrameworkVersion`.

A node can optionally reference another `FrameworkNode` as its parent.

```text
Framework
    |
    +-- FrameworkVersion
            |
            +-- FrameworkNode
            +-- FrameworkNode
            +-- FrameworkNode
```

Core fields include:

```text
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
```

`depth` and `path` are maintained as tree metadata.

---

## 5. Framework Node Types

The current node types are:

```text
SECTION
SUBSECTION
DISCLOSURE
INDICATOR
SUBINDICATOR
```

### SECTION

A major framework-level grouping.

Example:

```text
TOPIC-STANDARDS
```

### SUBSECTION

A subdivision inside a section.

Examples:

```text
GRI-300
GRI-302
```

### DISCLOSURE

A reporting/disclosure-level requirement.

Examples:

```text
302-1
302-2
```

### INDICATOR

A more granular reporting indicator when required by the framework.

### SUBINDICATOR

A further subdivision of an indicator.

The node type describes structural role. It does not define an M4 datapoint.

---

## 6. Framework Tree

The tree is represented using the self-referencing `parent` relationship.

Representative hierarchy:

```text
GRI-2021
|
+-- GRI-2
|
+-- UNIVERSAL-STANDARDS
|   +-- ORGANIZATIONAL-PROFILE
|   +-- REPORTING-PRACTICES
|
+-- TOPIC-STANDARDS
    +-- GRI-300
        +-- GRI-302
            +-- 302-1
            +-- 302-2
```

The database stores parent-child relationships. `depth` and `path` provide deterministic tree metadata.

---

## 7. Tree Rules and Invariants

### Same-version parent

A node's parent must belong to the same framework version.

### No self-parenting

A node cannot be its own parent.

### No cycles

A node cannot be moved below one of its descendants.

Invalid:

```text
A
+-- B
    +-- C
        +-- A
```

### Node-code uniqueness

The combination:

```text
framework_version + code
```

must be unique.

### Deterministic sibling ordering

Sibling nodes are ordered using:

```text
display_order
code
```

### Depth

Root nodes have:

```text
depth = 0
```

Each child has:

```text
depth = parent.depth + 1
```

### Path

Example:

```text
/TOPIC-STANDARDS/
/TOPIC-STANDARDS/GRI-300/
/TOPIC-STANDARDS/GRI-300/GRI-302/
/TOPIC-STANDARDS/GRI-300/GRI-302/302-1/
```

When a node is moved, its descendants are rebuilt so their depth/path metadata remains correct.

---

## 8. FrameworkTreeService

The tree service is responsible for:

- Creating framework nodes
- Moving framework nodes
- Rebuilding subtree metadata
- Retrieving framework trees
- Validating hierarchy integrity

It does not handle:

- RBAC
- Datapoint mapping
- Report generation
- Calculations

When a node is moved, the node's metadata is recalculated and the affected descendant subtree is rebuilt.

---

## 9. DatapointMapping

`DatapointMapping` connects a framework node to a canonical M4 datapoint.

```text
FrameworkNode
      |
      v
DatapointMapping
      |
      v
M4 Datapoint
```

A framework node may map to one or more canonical datapoints.

Example:

```text
GRI 302-1
     |
     +-- DatapointMapping
             |
             +-- M4 Energy Consumption Datapoint
```

The same canonical datapoint can be reused by different framework nodes where appropriate.

This supports the platform's "collect once, report many" architecture.

---

## 10. M4 Datapoint Reference

M7 does not create a second datapoint model.

The canonical datapoint remains owned by the M4 Datapoint Catalog.

M7 references it with a foreign key:

```python
datapoint = models.ForeignKey(
    "datapoints.Datapoint",
    ...
)
```

Therefore:

```text
M4 Datapoint
    |
    v
DatapointMapping
    ^
    |
FrameworkNode
```

M7 stores the mapping relationship and mapping metadata. It does not duplicate the M4 datapoint definition.

---

## 11. Mapping Types

### DIRECT

The framework node directly corresponds to a canonical datapoint.

### NARRATIVE

The framework requirement requires a narrative/manual response. M7 stores the mapping foundation but does not implement the future narrative response workflow.

### CALCULATED

The framework node depends on a calculated or derived value. M7 stores metadata only; calculation execution belongs to a future calculation/reporting layer.

---

## 12. Mapping Metadata

The mapping model supports metadata such as:

```text
mapping_type
aggregation
transform_expression
is_primary
confidence
mapping_note
reviewed_at
```

`transform_expression` is metadata only. M7 does not execute arbitrary transformation expressions.

Only active canonical datapoints should be mapped.

Duplicate mappings for the same:

```text
framework_node + datapoint
```

are controlled at the database level.

---

## 13. API

All M7 APIs are registered under:

```text
/api/frameworks/
```

Authentication uses the existing project DRF configuration. RBAC is intentionally deferred.

### Framework

```http
GET   /api/frameworks/
POST  /api/frameworks/
GET   /api/frameworks/<framework_id>/
PUT   /api/frameworks/<framework_id>/
PATCH /api/frameworks/<framework_id>/
```

### Framework Versions

```http
GET   /api/frameworks/<framework_id>/versions/
POST  /api/frameworks/<framework_id>/versions/

GET   /api/frameworks/versions/<version_id>/
PUT   /api/frameworks/versions/<version_id>/
PATCH /api/frameworks/versions/<version_id>/
```

### Framework Node

```http
GET /api/frameworks/nodes/<node_id>/
```

### Complete Framework Tree

```http
GET /api/frameworks/versions/<version_id>/tree/
```

The tree endpoint returns the complete nested hierarchy in one request.

Example:

```json
{
    "framework": {
        "id": "...",
        "code": "GRI",
        "name": "Global Reporting Initiative"
    },
    "version": {
        "id": "...",
        "code": "GRI-2021",
        "name": "GRI 2021"
    },
    "tree": [
        {
            "id": "...",
            "code": "TOPIC-STANDARDS",
            "title": "Topic Standards",
            "node_type": "SECTION",
            "depth": 0,
            "path": "/TOPIC-STANDARDS/",
            "children": []
        }
    ]
}
```

### Datapoint Mappings

```http
GET    /api/frameworks/mappings/
POST   /api/frameworks/mappings/
GET    /api/frameworks/mappings/<mapping_id>/
PUT    /api/frameworks/mappings/<mapping_id>/
PATCH  /api/frameworks/mappings/<mapping_id>/
DELETE /api/frameworks/mappings/<mapping_id>/
```

Example create request:

```json
{
    "framework_node": "<framework-node-id>",
    "datapoint": "<m4-datapoint-id>",
    "mapping_type": "DIRECT",
    "aggregation": "NONE",
    "is_primary": true,
    "confidence": "CONFIRMED",
    "mapping_note": "Representative framework mapping."
}
```

---

## 14. Mapping Filters

Filter by framework node:

```http
GET /api/frameworks/mappings/?framework_node=<node_id>
```

Filter by canonical datapoint:

```http
GET /api/frameworks/mappings/?datapoint=<datapoint_id>
```

Filter by mapping type:

```http
GET /api/frameworks/mappings/?mapping_type=DIRECT
GET /api/frameworks/mappings/?mapping_type=NARRATIVE
GET /api/frameworks/mappings/?mapping_type=CALCULATED
```

Filter by confidence:

```http
GET /api/frameworks/mappings/?confidence=CONFIRMED
GET /api/frameworks/mappings/?confidence=PROVISIONAL
```

Filters can be combined:

```http
GET /api/frameworks/mappings/?framework_node=<node_id>&mapping_type=DIRECT
```

---

## 15. Authentication

M7 uses the existing project-wide DRF authentication configuration.

The current project uses session authentication and authenticated-user permissions.

Conceptually:

```text
HTTP Request
     |
     v
DRF Authentication
     |
     v
Authenticated User
     |
     v
M7 API View
```

M7 does not implement a separate authentication mechanism.

RBAC/role-specific authorization is intentionally deferred.

---

## 16. Content Seed / Import Strategy

M7 contains a small representative framework seed to prove the hierarchy and mapping architecture.

It is intentionally not a complete GRI or BRSR content population.

Representative hierarchy:

```text
GRI
+-- GRI-2021
    +-- GRI-2
    +-- UNIVERSAL-STANDARDS
    |   +-- ORGANIZATIONAL-PROFILE
    |   +-- REPORTING-PRACTICES
    +-- TOPIC-STANDARDS
        +-- GRI-300
            +-- GRI-302
                +-- 302-1
                +-- 302-2
```

Seed command:

```bash
python manage.py seed_frameworks
```

The seed is designed to be idempotent. Running it repeatedly should not create duplicate framework, version, or node records.

### Content Governance

Official framework content should not be independently invented or extensively paraphrased.

Large-scale GRI/BRSR population should be handled as a controlled content workstream using reviewed source material.

---

## 17. Testing

M7 should cover:

- Framework creation
- Framework version creation
- Framework/node relationships
- Multi-level node hierarchy
- Node path calculation
- Node depth calculation
- Parent validation
- Cycle prevention
- Node-code uniqueness
- Deterministic sibling ordering
- Complete tree API response
- Datapoint mapping creation
- Mapping retrieval
- Mapping filtering
- Duplicate mapping protection
- Active datapoint validation
- Mapping update/delete behavior
- Seed idempotency

Basic checks:

```bash
python manage.py check
python manage.py makemigrations --check
```

Seed verification:

```bash
python manage.py seed_frameworks
```

Run the seed more than once and verify that duplicates are not created.

---

## 18. Representative Mapping Flow

```text
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
```

Example:

```text
GRI
+-- GRI-2021
    +-- TOPIC-STANDARDS
        +-- GRI-300
            +-- GRI-302
                +-- 302-1
                    |
                    v
              DatapointMapping
                    |
                    v
              M4 Datapoint
```

The mapping connects the framework requirement with the reusable canonical datapoint.

---

## 19. Relationship to Future M8 Report Runs

M7 provides the framework structure and mapping foundation for future reporting functionality.

Expected future flow:

```text
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
```

M7 stops before report-run and answer-storage stages.

M8 can use the framework tree to determine:

- which disclosures exist
- their hierarchy
- their ordering
- which disclosures are answerable
- which canonical datapoints are associated with them
- which mapping type applies

---

## 20. What Remains for M8

The following are intentionally outside M7.

### Report Run / Version

M8 will need models representing a particular reporting execution or report version.

```text
Report
    |
    +-- ReportRun
```

### Disclosure Assignment

M8 will determine which disclosures are assigned to users, teams, or organizational contexts.

### Answer Storage

The appropriate answer/data module will own company responses.

M7 does not store company answers.

### Narrative Response Workflow

M7 identifies narrative/manual requirements but does not implement drafting, submission, approval, review, or locking workflows.

### Calculation Engine

M7 may store calculated/derived mapping metadata, but calculation execution belongs to a future calculation/reporting layer.

### Report Generation

Future reporting functionality will generate PDF, Excel, and other outputs.

### Auditor Access

Auditor-specific permissions and workflows are outside the current M7 scope.

---

## 21. Architectural Principle

The key architectural principle is separation of concerns:

```text
M4
Canonical Datapoint Definition
        |
        v
M7
Framework Structure + Mapping
        |
        v
Future Reporting Modules
Report Runs + Answers + Output
```

M7 does not redefine the meaning of a datapoint.

Instead, it answers:

> Where does this canonical datapoint participate in this framework?

This allows the same canonical datapoint to be reused across multiple frameworks and disclosures without maintaining duplicated question definitions.

---

## 22. M7 Completion Boundary

The M7 foundation is considered complete when:

1. Frameworks and framework versions can be created and retrieved.
2. Framework nodes can represent multi-level hierarchies.
3. Parent-child relationships are validated.
4. Cyclic relationships are prevented.
5. Node ordering is deterministic.
6. Framework tree metadata (`depth` and `path`) is maintained.
7. A complete framework tree can be retrieved through one API request.
8. Datapoint mappings reference the canonical M4 datapoint model.
9. Duplicate mappings are controlled.
10. Mapping types and metadata can be stored.
11. Representative framework content can be seeded idempotently.
12. Authentication follows the existing project architecture.
13. Tests and Django checks can validate the implementation.
14. The architecture remains independent of future M8 report-run functionality.

---

## 23. Summary

M7 establishes the framework catalog and mapping foundation for the ESG platform.

Final conceptual model:

```text
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
```

The framework tree is versioned and validated, while canonical datapoints remain owned by M4.

This provides a stable foundation for future reporting modules to consume framework disclosures, resolve associated datapoints, collect responses, execute report runs, and generate reporting outputs.
