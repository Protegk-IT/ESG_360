# M8 Reporting Run and Framework Snapshot Foundation

****Issue:**** #35 — M8 Reporting Run and Framework Snapshot Foundation

****Module:**** M8 — Reporting

****Owner:**** Rajan

****Base branch:**** latest `develop`

****Primary backend area:**** `backend/apps/reporting/`

**---**

## 1. Problem Statement

M8 establishes the first stable reporting foundation for the ESG platform.

The reporting system needs a persistent concept representing a particular reporting execution context. A report must be associated with:

- a selected reporting period from M3;

- a selected framework version from M7;

- the authenticated user who created/requested the run;

- a controlled lifecycle;

- a historical copy of the framework structure and mappings used by that run.

The central problem is that M7 framework data is live and mutable. Framework nodes and datapoint mappings can be edited after a report run has been created. If a report relied directly on those live rows, a historical report definition could silently change.

M8 therefore introduces a ****frozen framework snapshot****.

The fundamental design is:

```text

ReportingPeriod (M3)

        +

FrameworkVersion (M7)

        |

        v

    ReportRun

        |

        | freeze

        v

FrameworkSnapshot

        |

        +--> SnapshotNode

        |        |

        |        +--> SnapshotMapping

        |

        v

Historical / immutable reporting structure

```

The snapshot captures the M7 structure at freeze time without introducing unfinished M5 answer/submission models or M6 calculated-result dependencies.

**---**

## 2. Scope of M8

### In scope

1. `ReportRun`

2. `FrameworkSnapshot`

3. `SnapshotNode`

4. `SnapshotMapping`

5. transactional freeze service

6. ReportRun CRUD API

7. freeze API

8. frozen snapshot retrieval API

9. Django Admin support

10. serializers

11. RBAC integration

12. immutable snapshot behavior

13. automated tests

14. module documentation

### Explicitly out of scope

M8 does ****not**** implement:

- M5 Answer models

- M5 Submission models

- M5 DataRequest models

- answer/value resolution

- M6 calculated results

- emission calculations

- disclosure assignment

- narrative workflow

- PDF generation

- Excel generation

- final report rendering

- auditor workflow

- materiality changes

- large framework-content population

- frontend reporting screens

This boundary was intentionally maintained so M8 does not invent future M5/M6 schemas.

**---**

## 3. Git Workflow Used

M8 was developed as an isolated issue branch rather than continuing development on the previous M7 feature branch.

The repository workflow follows the team's branch structure:

```text

main

  |

  +---- develop

          |

          +---- M8 issue/feature branch

```

The issue explicitly required starting from the latest `develop`.

The M8 implementation was kept isolated so that:

- M7 remains stable;

- M8 changes are independently reviewable;

- unfinished M5 work is not modified;

- the eventual merge happens through the team's normal integration workflow.

Final verification was performed before commit:

```powershell

python manage.py test apps.reporting

python manage.py check

python manage.py makemigrations --check --dry-run

git diff --check

```

Final verification result:

```text

207 tests

OK

System check identified no issues (0 silenced).

No changes detected

```

`git diff --check` produced no output, meaning no whitespace errors were detected.

**---**

## 4. Dependency Strategy

M8 reuses already accepted platform contracts.

The important rule used during implementation was:

*>* ****Reuse existing module contracts; do not modify upstream modules merely to make M8 work.****

The main dependencies are:

```text

M3 Reporting Periods

M4 Datapoint Catalog

M7 Framework / FrameworkVersion / FrameworkNode / DatapointMapping

Accounts / RBAC

Core / BaseModel / Activity logging

```

These modules were inspected and consumed as dependencies.

Where test data required upstream objects, the M8 tests created the minimum required dependency objects ****inside the M8 test suite****.

The upstream modules themselves were not changed simply to accommodate M8 tests.

This was especially important because M5 was still under development.

**---**

## 5. Reuse of Core Platform Infrastructure

### 5.1 BaseModel

M8 reused the central `BaseModel` from:

```text

apps.core.models

```

The base model provides the common platform identity and timestamp convention:

```text

id

created_at

updated_at

```

M8 models therefore follow the repository-wide model convention instead of redefining UUID and timestamp fields independently.

Conceptually:

```python

class ReportRun(BaseModel):

    ...

```

and similarly for snapshot entities.

This gives M8 consistent identity and timestamp behavior with the rest of the platform.

### 5.2 Activity Logging

The platform contains an `ActivityLogMixin` in the core area.

The mixin provides centralized activity auditing for model operations such as:

```text

CREATE

UPDATE

DELETE

```

along with request metadata where available.

M8 follows the existing platform audit approach rather than inventing a separate M8 audit system.

**---**

## 6. Central RBAC Architecture

M8 does not create an independent authorization framework.

The project already provides:

```text

RBACModelViewSet

        |

        +--> IsAuthenticated

        |

        +--> HasRolePermission

        |

        +--> RBACService

```

M8 reuses this centralized authorization mechanism.

The M8 ViewSet derives from:

```python

RBACModelViewSet

```

The authorization flow is:

```text

HTTP request

     |

     v

IsAuthenticated

     |

     v

HasRolePermission

     |

     v

canonical permission code

     |

     v

RBACService

     |

     v

allow / deny

```

Reporting reads require authentication. Report-run creation, updates,

deletion, and freezing require the existing canonical permission:

```text

report.create_run

```

The implementation deliberately does not invent separate reporting permissions

such as:

```text

framework_mapping.manage

```

**---**

## 7. M3 Reporting Period Dependency

M8 does not recreate reporting periods.

It reuses:

```text

apps.periods.ReportingPeriod

```

A `ReportRun` references an existing M3 reporting period.

```text

ReportingPeriod

       |

       | selected for

       v

   ReportRun

```

M3 remains responsible for its own rules such as:

- valid dates;

- period hierarchy;

- period status;

- annual overlap;

- baseline-year constraints.

M8 consumes the valid M3 object rather than duplicating those rules.

**---**

## 8. M7 Framework Dependency

M8 uses the accepted M7 framework structures:

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

Datapoint

```

M8 does not duplicate the live framework catalog.

A `ReportRun` stores the selected:

```text

FrameworkVersion

```

and the freeze service reads the current M7 structure from that version.

**---**

## 9. M4 Datapoint Dependency

M8 uses the M4 datapoint catalog through M7's `DatapointMapping`.

The snapshot captures important datapoint identity required for future reporting:

```text

source_datapoint_id

canonical_datapoint_code

```

M8 does not store M5 answer data or M6 calculated values.

**---**

## 10. M8 Domain Model

M8 introduces four primary models:

```text

ReportRun

    |

    +---- FrameworkSnapshot

              |

              +---- SnapshotNode

                        |

                        +---- SnapshotMapping

```

**---**

## 11. ReportRun

`ReportRun` represents one reporting execution context.

It connects:

```text

ReportingPeriod

        +

FrameworkVersion

        +

created_by

```

It also contains lifecycle/freeze information:

```text

reporting_period

framework_version

created_by

status

is_frozen

snapshot_frozen_at

metadata

created_at

updated_at

```

The `metadata` field provides a controlled extension point for run-level information without adding speculative M5/M6 fields.

**---**

## 12. ReportRun Lifecycle

The lifecycle is intentionally small:

```text

DRAFT

  |

  | freeze

  v

FROZEN

```

Once frozen:

- framework version cannot silently change;

- reporting period cannot silently change;

- normal API modification is blocked;

- normal API deletion is blocked;

- the snapshot represents historical reporting structure.

**---**

## 13. FrameworkSnapshot

`FrameworkSnapshot` represents the immutable copy of the framework identity used by a report run.

It stores:

```text

report_run

source_framework_id

source_framework_version_id

framework_code

framework_name

version_code

version_name

frozen_at

```

The `source_*` fields identify the origin, while the copied identity fields preserve historical identifying information directly.

The snapshot therefore does not depend on the live M7 framework rows as its only source of truth.

**---**

## 14. SnapshotNode

`SnapshotNode` is the historical copy of a M7 `FrameworkNode`.

It captures:

```text

source_node_id

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

metadata

```

Parent relationships are reconstructed inside the snapshot so the historical tree does not depend solely on the mutable M7 parent relationship.

**---**

## 15. SnapshotMapping

`SnapshotMapping` captures the M7 datapoint mapping associated with a frozen node.

Important fields include:

```text

source_mapping_id

source_datapoint_id

canonical_datapoint_code

mapping_type

aggregation

transform_expression

is_primary

confidence

mapping_note

reviewed_at

display_order

metadata

```

This preserves the mapping definition used by the report at freeze time.

**---**

## 16. Why Snapshot Instead of Direct M7 References?

A direct design such as:

```text

ReportRun

    |

    +--> FrameworkVersion

```

would not be sufficient.

Suppose M7 initially contains:

```text

GRI-2021

    |

    +-- 302-1

    +-- 302-2

```

A report run is frozen.

Later M7 changes:

```text

GRI-2021

    |

    +-- 302-1

    +-- 302-2

    +-- 302-3

```

If M8 queried the live M7 structure, the old report could unexpectedly see `302-3`.

With a snapshot:

```text

M7 at freeze

    |

    v

M8 snapshot

    |

    +-- 302-1

    +-- 302-2

M7 later changes

    |

    v

M8 snapshot

    |

    +-- 302-1

    +-- 302-2

```

The historical report definition remains unchanged.

**---**

## 17. Freeze Service

The central business operation is:

```text

freeze_report_run()

```

located in:

```text

apps.reporting.services

```

The view does not directly implement snapshot creation.

Responsibility is separated as:

```text

View

 |

 +--> HTTP handling

 +--> authentication/RBAC

 +--> request/response serialization

 |

 v

Service

 |

 +--> business rules

 +--> transaction

 +--> snapshot creation

 +--> lifecycle transition

```

This keeps domain logic out of the HTTP layer.

**---**

## 18. Transactional Freeze

The freeze service uses:

```python

transaction.atomic()

```

The complete operation is one database transaction:

```text

BEGIN TRANSACTION

       |

       v

lock ReportRun

       |

       v

verify not already frozen

       |

       v

create FrameworkSnapshot

       |

       v

copy FrameworkNodes

       |

       v

reconstruct parent relationships

       |

       v

copy DatapointMappings

       |

       v

mark ReportRun FROZEN

       |

       v

COMMIT

```

If any operation fails:

```text

ROLLBACK

```

Therefore the database cannot retain a partial snapshot.

**---**

## 19. Concurrency Protection

The freeze service locks the `ReportRun` using:

```python

select_for_update()

```

The frozen state is checked again after acquiring the database lock.

This protects against concurrent freeze requests:

```text

Request A ── lock ── freeze ── commit

Request B ─────────── wait

                         |

                         v

                    sees FROZEN

                         |

                         v

                       reject

```

**---**

## 20. Re-freezing Behavior

The freeze operation is intentionally controlled and non-idempotent.

If a report run is already frozen:

```text

POST /report-runs/<id>/freeze/

```

is rejected with a validation error.

This prevents accidental multiple snapshots for the same run.

**---**

## 21. Deterministic Snapshot Ordering

Framework nodes are ordered using:

```text

path

display_order

code

id

```

Mappings are ordered using:

```text

primary status

datapoint code

mapping id

```

and receive a snapshot-local `display_order`.

This gives predictable snapshot structure and stable automated tests.

**---**

## 22. Parent Relationship Reconstruction

During freeze, M7 nodes are mapped to their newly created snapshot nodes.

Conceptually:

```text

M7 node ID

     |

     v

SnapshotNode

```

After all snapshot nodes exist, the service reconstructs:

```text

SnapshotNode.parent

```

using the corresponding snapshot parent.

Thus the historical tree is self-contained.

**---**

## 23. Immutable Snapshot Design

Snapshot entities are treated as immutable after creation.

The normal M8 API exposes them as read-only.

Django Admin also prevents normal creation, modification and deletion of:

```text

FrameworkSnapshot

SnapshotNode

SnapshotMapping

```

They are created through the controlled freeze service.

**---**

## 24. Serializer Architecture

M8 uses Django REST Framework serializers:

```text

ReportRunSerializer

        |

        +--> normal run representation

ReportRunDetailSerializer

        |

        +--> detailed run

        +--> framework snapshot

FrameworkSnapshotSerializer

        |

        +--> snapshot

        +--> nodes

SnapshotNodeSerializer

        |

        +--> frozen node

        +--> nested mappings

SnapshotMappingSerializer

        |

        +--> frozen mapping

```

Snapshot serializers are read-only.

The ReportRun serializer also obtains `created_by` from the authenticated request rather than trusting client input.

**---**

## 25. API Architecture

CRUD:

```text

GET     /api/reporting/report-runs/

POST    /api/reporting/report-runs/

GET     /api/reporting/report-runs/<uuid>/

PATCH   /api/reporting/report-runs/<uuid>/

DELETE  /api/reporting/report-runs/<uuid>/

```

Freeze:

```text

POST /api/reporting/report-runs/<uuid>/freeze/

```

Snapshot:

```text

GET /api/reporting/report-runs/<uuid>/snapshot/

```

The list API also supports filtering by:

```text

reporting_period

framework_version

status

```

**---**

## 26. Frozen CRUD Protection

For update, partial update and delete, the ViewSet checks:

```text

is_frozen

```

A frozen report run cannot be modified or deleted through the normal API.

This protects the historical reporting context.

**---**

## 27. Freeze API Responsibility

The freeze endpoint:

1. authenticates the request;

2. checks canonical RBAC permission;

3. retrieves the ReportRun;

4. calls `freeze_report_run()`;

5. converts domain validation errors to DRF responses;

6. returns the frozen ReportRun representation.

The view does not manually create snapshot rows.

**---**

## 28. Snapshot API Responsibility

The snapshot endpoint:

```text

GET /api/reporting/report-runs/<uuid>/snapshot/

```

retrieves the frozen structure.

An unfrozen run does not expose a snapshot.

The endpoint is read-only and does not create or modify snapshot records.

**---**

## 29. Admin Design

Django Admin was configured for:

```text

ReportRun

FrameworkSnapshot

SnapshotNode

SnapshotMapping

```

ReportRun provides visibility into:

```text

reporting period

framework version

creator

status

freeze timestamp

```

Snapshot entities are intentionally read-only.

The Admin prevents normal:

```text

add

change

delete

```

operations on immutable snapshot records.

**---**

## 30. Testing Strategy

The M8 tests live under:

```text

apps.reporting.tests

```

The suite uses existing upstream models as dependencies but does not modify those upstream modules.

The M8 tests create the minimum required dependency objects:

```text

User

ReportingPeriod

Framework

FrameworkVersion

FrameworkNode

Datapoint

DatapointMapping

```

inside the test database.

Django creates and destroys the temporary test database automatically.

**---**

## 31. Why Dependency Objects Are Created in M8 Tests

M8 needs representative M3/M4/M7 data.

Instead of changing upstream seed data or upstream modules, the test suite constructs controlled fixtures.

Benefits:

- isolated tests;

- repeatability;

- no production-data dependency;

- no upstream module changes;

- explicit test scenarios;

- clean temporary database.

This was particularly important because M5 was unfinished.

**---**

## 32. Adapting to Existing Upstream Contracts

M8 tests consume upstream models according to their actual choices and relationships.

For example, an initial test fixture attempted to use an invalid M7 node type:

```text

DATAPOINT

```

The actual M7 model did not define that choice.

Rather than modifying M7, the M8 test fixture was corrected to use a valid M7 node type.

This follows the rule:

*> M8 adapts to established upstream contracts rather than redefining them.*

**---**

## 33. Automated Test Coverage

The final module test suite contains:

```text

207 tests

```

Final command:

```powershell

python manage.py test apps.reporting

```

Result:

```text

Ran 207 tests

OK

```

Coverage includes:

- ReportRun creation;

- validation;

- service input validation for freeze and dataset resolution;

- rejection of frozen runs that have no framework snapshot;

- empty text values remaining unresolved;

- retrieval;

- filtering;

- update/delete behavior;

- frozen protection;

- freeze operation;

- snapshot creation;

- mapping identity;

- parent relationships;

- deterministic ordering;

- transaction rollback;

- historical isolation;

- authentication;

- RBAC;

- snapshot API.

**---**

## 34. Historical Isolation Test

A key acceptance scenario is:

```text

freeze M8

   |

   v

modify M7

   |

   v

retrieve M8 snapshot

```

The snapshot remains unchanged.

Conceptually:

```text

Before freeze:

302-1

302-2

freeze

Modify M7:

302-1 title changed

302-3 added

M8 snapshot:

302-1 -> original title

302-2 -> unchanged

302-3 -> absent

```

This proves the snapshot is historical rather than a live view of M7.

**---**

## 35. Transaction Rollback Test

Tests intentionally cause failures during snapshot creation and verify:

```text

no partial FrameworkSnapshot

no partial SnapshotNode

no partial SnapshotMapping

ReportRun remains unfrozen

```

This directly verifies the transactional acceptance criterion.

**---**

## 36. Authentication and RBAC Tests

Tests verify:

- unauthenticated access is rejected where authentication is required;

- administrative operations use the centralized RBAC mechanism;

- the canonical permission is evaluated through the existing RBAC service.

M8 does not duplicate permission logic.

**---**

## 37. Migration and System Verification

Executed:

```powershell

python manage.py check

```

Result:

```text

System check identified no issues (0 silenced).

```

Executed:

```powershell

python manage.py makemigrations --check --dry-run

```

Result:

```text

No changes detected

```

Executed:

```powershell

git diff --check

```

Result:

```text

No output / no whitespace errors

```

**---**

## 38. M5/M6 Integration Boundary

M8 intentionally stops before value resolution.

The future architecture is:

```text

FrameworkSnapshot

      |

      +--> SnapshotNode

      |

      +--> SnapshotMapping

                    |

                    v

             Value Provider

                    |

             +------+------+

             |             |

             v             v

            M5            M6

       captured values   calculated results

             |             |

             +------+------+

                    |

                    v

              Report Output

```

M8 does not assume the final M5/M6 schemas.

This allows the snapshot model to remain stable while future value providers are introduced.

**---**

## 39. Separation of Responsibilities

### Models

Responsible for:

- persistence;

- relationships;

- lifecycle state;

- database representation.

### Serializers

Responsible for:

- API representation;

- request validation;

- authenticated creator assignment;

- read-only snapshot representation.

### Views

Responsible for:

- HTTP concerns;

- authentication;

- RBAC;

- object retrieval;

- HTTP responses.

### Services

Responsible for:

- freeze business logic;

- transaction management;

- snapshot generation;

- concurrency control;

- lifecycle transition.

### Admin

Responsible for:

- administrative visibility;

- controlled read-only snapshot inspection.

### Tests

Responsible for:

- validating M8 behavior;

- creating isolated dependency fixtures;

- protecting the M8 contract.

This separation keeps business logic out of HTTP and Admin code.

**---**

## 40. Performance Considerations

The implementation uses related-object loading where appropriate.

ReportRun querysets use:

```text

select_related(

    reporting_period,

    framework_version,

    framework_version__framework,

    created_by

)

```

Snapshot creation uses related-object loading and prefetching for framework nodes and mappings.

This reduces unnecessary repeated database queries during serialization and snapshot generation.

**---**

## 41. End-to-End Example

An administrator selects:

```text

Reporting Period:

FY 2025-26

Framework:

GRI

Framework Version:

GRI-2021

```

The API creates:

```text

ReportRun

status = DRAFT

```

Then:

```text

POST /api/reporting/report-runs/<id>/freeze/

```

The service copies the current framework:

```text

FrameworkVersion

    |

    +-- FrameworkNode 1

    +-- FrameworkNode 2

    +-- FrameworkNode 3

            |

            +-- DatapointMapping

```

into:

```text

FrameworkSnapshot

    |

    +-- SnapshotNode 1

    +-- SnapshotNode 2

    +-- SnapshotNode 3

            |

            +-- SnapshotMapping

```

The ReportRun becomes:

```text

FROZEN

```

Future M7 changes do not affect these snapshot records.

**---**

## 42. Historical Data Principle

The fundamental M8 rule is:

*>* ****A frozen report run represents the framework definition as it existed when the run was frozen.****

Therefore live M7 can continue evolving independently while M8 historical snapshots remain stable.

This is essential for reproducible reporting.

**---**

## 43. Final Acceptance Status

### 1. Report runs can be created

Implemented through the ReportRun API.

### 2. Framework structure can be frozen transactionally

Implemented through `freeze_report_run()` and `transaction.atomic()`.

### 3. Frozen structure is deterministic and immutable

Implemented through deterministic ordering and read-only snapshot behavior.

### 4. Live M7 changes do not mutate historical snapshots

Covered by historical-isolation tests.

### 5. No hard M5 dependency

No M5 models or speculative M5 schema were introduced.

### 6. No fake answer/calculation schema

M8 stores framework and mapping identity only.

### 7. APIs expose run metadata and snapshot

Implemented through CRUD, freeze and snapshot endpoints.

### 8. Authorization follows platform contract

Implemented through centralized authentication/RBAC.

### 9. Automated verification passes

```text

207 tests — OK

Django check — OK

Migration drift check — OK

git diff --check — OK

```

### 10. Documentation marks future M5/M6 work

This document defines the future value-resolution boundary.

The focused reporting service verification also covers the current
value-resolution boundary:

```powershell

python manage.py test apps.reporting.tests.test_services

```

Result:

```text

Ran 59 tests

OK

```

**---**

## 44. Final Architecture

```text

                         PLATFORM

                            |

             +--------------+--------------+

             |                             |

          Core/BaseModel                Accounts/RBAC

             |                             |

             +--------------+--------------+

                            |

                           M8

                            |

                    +-------+-------+

                    |               |

              ReportingPeriod   FrameworkVersion

                    |               |

                    +-------+-------+

                            |

                        ReportRun

                            |

                         Freeze

                            |

                 +----------+----------+

                 |                     |

          FrameworkSnapshot       FROZEN STATE

                 |

          +------+------+

          |             |

    SnapshotNode   SnapshotNode

          |

    SnapshotMapping

          |

          v

 Historical framework definition

          |

          v

 Future Value Resolution

          |

       +--+--+

       |     |

      M5     M6

       |     |

       +--+--+

          |

     Future Report Output

```

**---**

## 45. Engineering Principles Used

1. ****Reuse established platform contracts.****

2. ****Reuse the central BaseModel.****

3. ****Use centralized RBAC instead of module-specific authorization.****

4. ****Keep M3, M4 and M7 as the source of truth for their domains.****

5. ****Use snapshots to preserve historical reporting definitions.****

6. ****Keep snapshot creation transactional.****

7. ****Protect concurrent freeze operations.****

8. ****Keep immutable snapshot data read-only after creation.****

9. ****Do not depend on unfinished M5/M6 schemas.****

10. ****Test upstream dependencies through M8-owned fixtures rather than modifying upstream modules.****

11. ****Separate HTTP, business logic, persistence and authorization responsibilities.****

12. ****Prefer a small stable foundation over premature complete report generation.****

**---**

## 46. Final Development Status

M8 Reporting Run and Framework Snapshot Foundation has completed its implementation and verification stage.

```text

M8 implementation       COMPLETE

M8 automated tests       207 / 207 PASS

Django system check      PASS

Migration drift check    PASS

Git whitespace check     PASS

M5 dependency            NONE

M6 dependency            NONE

Snapshot isolation       VERIFIED

Transactional freeze     VERIFIED

RBAC integration         VERIFIED

```

## 47. How to Understand This Module After Several Months

When returning to M8 later, remember the module in this order:

### Step 1 — What problem does M8 solve?

M7 is live and mutable. A report needs a historical, reproducible definition of the framework that was used.

Therefore:

`ReportRun + Freeze → immutable framework snapshot`

### Step 2 — What is a ReportRun?

A ReportRun is the reporting execution context:

`ReportingPeriod + FrameworkVersion + created_by + lifecycle`

It starts as `DRAFT` and becomes `FROZEN`.

### Step 3 — What happens during freeze?

The service:

1. locks the ReportRun;
2. verifies it is not already frozen;
3. creates FrameworkSnapshot;
4. copies M7 FrameworkNodes into SnapshotNodes;
5. reconstructs parent relationships;
6. copies M7 DatapointMappings into SnapshotMappings;
7. marks the ReportRun as FROZEN;
8. commits everything atomically.

### Step 4 — Why are there four M8 models?

```text
ReportRun
   |
   v
FrameworkSnapshot
   |
   v
SnapshotNode
   |
   v
SnapshotMapping
```

The first two identify the reporting context and framework version. The last two preserve the framework tree and datapoint mappings used by that run.

### Step 5 — What does M8 deliberately NOT contain?

Do not expect answer/value/calculation/report-generation logic here.

Those belong to later platform capabilities:

```text
M8 snapshot
    |
    +--> future M5 values/submissions
    |
    +--> future M6 calculations
    |
    +--> future report output
```

M8 intentionally remains independent of unfinished M5/M6 schemas.

### Step 6 — How does authorization work?

Never look for an M8-specific RBAC implementation.

Use the platform contract:

```text
User
  ↓
UserRoleAssignment
  ↓
Role
  ↓
Permission
  ↓
RBACService
  ↓
HasRolePermission / RBACModelViewSet
  ↓
M8 API
```

The canonical reporting write permission used after the review correction is:

```text
report.create_run
```

Do not replace it with a framework-administration permission.

### Step 7 — How should M8 be changed in the future?

Preserve these invariants:

- frozen snapshots remain historical;
- freeze is transactional;
- concurrent freeze requests cannot create duplicate snapshots;
- M7 remains the live framework source;
- M8 does not create a second RBAC system;
- M8 does not invent M5/M6 schemas;
- snapshot records are not edited through normal APIs/Admin;
- business logic stays in services rather than views.

### Step 8 — Where should I look first?

```text
apps/reporting/models.py
    → domain entities and lifecycle

apps/reporting/services.py
    → freeze business operation

apps/reporting/serializers.py
    → API representation and validation

apps/reporting/views.py
    → authentication, RBAC, HTTP behavior

apps/reporting/urls.py
    → API routes

apps/reporting/admin.py
    → admin visibility/immutability

apps/reporting/tests/
    → executable specification of the module

docs/modules/reporting-foundation.md
    → complete architecture record
```

### Step 9 — The one-sentence mental model

> **M8 creates a ReportRun from an M3 reporting period and M7 framework version, then freezes the live M7 structure and mappings into an immutable historical snapshot using a transactional, centrally authorized workflow.**

---


Ater Review documentation :------

M8_Phase2_Value_Resolution_Review_Hardening.md


M8 Phase 2 — Approved M5 Value Resolution and Review Hardening
Purpose
M8 Phase 2 adds the value-resolution layer on top of the frozen M8 reporting structure.

M8 Phase 1 answers:

What framework structure and datapoint mappings does this report contain?

M8 Phase 2 answers:

For each frozen mapping in this report, what approved captured value is currently available for the corresponding M4 canonical datapoint?

The architecture is:

M3 ReportingPeriod
        +
M7 FrameworkVersion
        |
        v
    M8 ReportRun
        |
      FREEZE
        |
        v
M8 FrameworkSnapshot
        |
        +--> SnapshotNode
        |       |
        |       +--> SnapshotMapping
        |                  |
        |                  | frozen M4 datapoint identity
        |                  v
        |            M5 DataRequest
        |                  |
        |             Submission
        |                  |
        |              APPROVED
        |                  |
        |                Answer
        |                  |
        |                  v
        +----------> ResolvedValue
Phase 2 does not create another M5 answer model. It reads the existing approved M5 captured values and exposes them through an M8 reporting-oriented representation.

1. Phase 1 vs Phase 2
Phase 1 — Structure freezing
Phase 1 freezes the selected framework structure and mapping identity:

Framework
FrameworkVersion
FrameworkNode
DatapointMapping
M4 datapoint identity
mapping order
reporting context
into:

FrameworkSnapshot
SnapshotNode
SnapshotMapping
It answers:

What exactly is this report supposed to contain?

Phase 2 — Value resolution
Phase 2 reads:

SnapshotMapping
        |
        v
M5 DataRequest
        |
        v
M5 Submission
        |
        v
M5 Answer
and produces:

ResolvedValue
It answers:

What approved value currently exists for each frozen mapping?

Therefore:

Phase 1 = freeze the question/report structure
Phase 2 = resolve the answer/value for that frozen structure
2. M7 Mapping vs M8 SnapshotMapping
M7 establishes the reusable framework relationship:

Framework requirement/question
            |
            v
     DatapointMapping
            |
            v
     M4 canonical Datapoint
The M7 mapping means:

This framework requirement uses this canonical datapoint.

M7 does not store the company's reporting-period answer.

M8 Phase 1 copies that relationship into SnapshotMapping so that the report has its own historical copy.

3. What Is Frozen?
M8 freezes the report structure and source identity.

It does not freeze the M5 answer itself.

At freeze time:

M7 live mapping
      |
      v
SnapshotMapping
      |
      +--> source_datapoint_id
      +--> canonical_datapoint_code
The snapshot preserves the historical meaning of the report.

The M5 answer remains in M5.

Therefore:

M8 Snapshot
    = historical report structure

M5 Answer
    = captured source value
This separation allows M7 to continue evolving without changing an already frozen report structure.

4. Phase 2 Resolver Architecture
The main service boundary is conceptually:

ReportValueResolver
        |
        v
CapturedValueProvider
        |
        v
ResolvedValue
The current provider is CapturedValueProvider because Phase 2 resolves approved M5 captured values.

A future provider can be added for M6:

SnapshotMapping
       |
       v
   ValueProvider
       |
       +-------------------+
       |                   |
       v                   v
M5 CapturedProvider   M6 CalculatedProvider
       |                   |
       v                   v
    Answer          CalculationResult
       |                   |
       +---------+---------+
                 |
                 v
           ResolvedValue
M8 therefore does not need to redesign the frozen snapshot when M6 integration is introduced.

5. Approved-Only Resolution Rule
Only values belonging to an approved submission are eligible:

DRAFT       X
SUBMITTED   X
REJECTED    X
REOPENED    X   (until approved again)
APPROVED    ✓
The effective rule is:

SnapshotMapping
+
same reporting period
+
same company scope
+
same frozen datapoint identity
+
SubmissionStatus.APPROVED
        |
        v
eligible M5 value
M8 performs no M5 workflow transition. It does not approve, reject, submit, modify, delete, or reopen M5 records.

The resolver is strictly read-only.

6. Historical Datapoint Identity
A critical Phase 2 review finding was the distinction between:

source_datapoint_id
and:

canonical_datapoint_code
The snapshot stores both.

The stable UUID is the primary operational identity.

The code is historical metadata.

Why the UUID Is Used
Suppose M4 originally contains:

Datapoint UUID = A
Code = ENERGY_TOTAL_CONSUMPTION
M8 freezes the mapping.

Later an administrator changes M4:

Datapoint UUID = A
Code = ENERGY_TOTAL_CONSUMPTION_KWH
The UUID remains A.

Therefore M8 must resolve using:

source_datapoint_id = A
rather than depending on the current live code.

The architectural rule is:

stable UUID
    ↓
historical operational identity

frozen code
    ↓
historical/display metadata
7. Historical Code Metadata
canonical_datapoint_code remains useful for:

historical display;

audit;

debugging;

report explanation;

compatibility with older snapshots.

However:

The frozen code is not the normal operational identity when source_datapoint_id exists.

Therefore:

source_datapoint_id
        ↓
primary lookup identity

canonical_datapoint_code
        ↓
historical/display metadata
8. Legacy Snapshot Fallback
Some older or manually-created snapshot records may not contain source_datapoint_id.

For those records, Phase 2 provides a narrow legacy fallback using the frozen canonical datapoint code.

Conceptually:

SnapshotMapping
      |
      +----------------------+
      |                      |
source_datapoint_id      no source ID
      |                      |
      v                      v
UUID lookup             frozen-code
                         fallback
      |                      |
      +----------+-----------+
                 |
                 v
             M5 value
The fallback is deliberately separated from the modern UUID-based lookup.

This prevents a modern mapping from silently falling back to a changed live code.

9. Company Scope
A reporting period is not sufficient to identify the correct M5 value.

For example:

Company A
FY2025
ENERGY_TOTAL
    = 100

Company B
FY2025
ENERGY_TOTAL
    = 500
A report belonging to Company A must never resolve Company B's value.

Therefore the resolver uses:

reporting period
+
company
+
datapoint identity
+
APPROVED submission
The M5 organization relationship is followed through:

DataRequest
    |
    v
OrgNode
    |
    v
Company
M8's ReportRun.company therefore defines the reporting tenant/company scope.

An unscoped ReportRun is rejected rather than allowing potentially mixed-company results.

10. Frozen Report Context
The complete report context is:

                    ReportRun
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
 FrameworkVersion  ReportingPeriod  Company
        |
        v
 FrameworkSnapshot
        |
        v
 SnapshotMapping
        |
        v
source_datapoint_id
        |
        v
      M5
The resolver is not simply:

datapoint → value
It is:

report
+
company
+
reporting period
+
frozen mapping
+
approved workflow state
        |
        v
resolved value
11. Resolved Value Output
Each mapping can produce one or more resolved values.

Multiple approved values are possible because M5 data is organization-scoped.

For example:

ENERGY_TOTAL_CONSUMPTION

    |
    +--> Plant A = 125.5 KWH
    |
    +--> Plant B = 210.0 KWH
    |
    +--> Plant C = 95.0 KWH
M8 does not automatically calculate the total.

The values remain separate and retain:

org_node_id
org_node_name
value
unit
provenance
for later aggregation/reporting logic.

12. Primitive Typed Values
M8 preserves the M5 typed answer representation.

Supported primitive representations include:

DECIMAL
INTEGER
TEXT
LONG_TEXT
BOOLEAN
SELECT
DATE
M8 does not convert everything into a string.

13. Falsy Values Are Still Valid Values
The resolver must not use:

if value:
to decide whether a value exists.

For example:

0
False
are legitimate values.

Therefore:

DECIMAL 0
    → RESOLVED

BOOLEAN False
    → RESOLVED
Only the explicit resolver status determines whether the value is unresolved.

14. SELECT Values
SELECT answers retain their typed structure rather than becoming arbitrary strings.

Where applicable, the resolved representation can retain:

option ID
option code
option label
15. TABLE Value Resolution
TABLE answers are not flattened into an opaque string.

The normalized M5 structure remains available:

Answer
   |
   +--> Row
   |     |
   |     +--> Cell
   |     +--> Cell
   |
   +--> Row
         |
         +--> Cell
         +--> Cell
M8 preserves:

fixed-row identity
dynamic-row label
row order
column identity/code
typed cell value
cell unit
Later report rendering can reconstruct the table without parsing a display string.

16. Provenance
Every resolved value retains source provenance.

Important identities include:

ReportRun
SnapshotMapping
canonical datapoint
DataRequest
Submission
Answer
OrgNode
Where available, approval and entry information is also retained:

approved_by
approved_at
entered_by
The source is identified as:

source_type = CAPTURED
This allows future report/audit interfaces to answer:

Where did this displayed reporting value come from?

17. Missing Value Behavior
A mapping can exist without an approved M5 value.

M8 does not fabricate zero, empty strings, or successful nulls.

Instead it explicitly returns:

{
  "status": "UNRESOLVED",
  "value": null
}
The distinction is:

MAPPING EXISTS
        +
NO APPROVED VALUE
        |
        v
UNRESOLVED
18. Phase 2 API
The resolved dataset is exposed through:

GET /api/reporting/report-runs/{id}/resolved-values/
The report run must be FROZEN.

The endpoint is:

authenticated
read-only
deterministically ordered
19. Phase 2 Output Example
{
  "snapshot_node_id": "...",
  "snapshot_mapping_id": "...",
  "canonical_datapoint_code": "ENERGY_TOTAL",
  "status": "RESOLVED",
  "data_type": "DECIMAL",
  "value": 125.5,
  "unit": {
    "id": "...",
    "code": "KWH",
    "name": "Kilowatt-hour"
  },
  "data_request_id": "...",
  "submission_id": "...",
  "answer_id": "...",
  "org_node_id": "...",
  "org_node_name": "Plant A",
  "provenance": {
    "source_type": "CAPTURED",
    "approved_by": {
      "id": "...",
      "username": "reviewer",
      "name": "Reviewer"
    },
    "approved_at": "...",
    "entered_by": {
      "id": "...",
      "username": "maker",
      "name": "Maker"
    }
  }
}
This output is a reporting dataset, not a final PDF/Excel report.

20. Complete M8 Phase 1 + Phase 2 Flow
                    M3
             ReportingPeriod
                    |
                    v
M7 FrameworkVersion
        |
        +--> FrameworkNode
        |
        +--> DatapointMapping
                    |
                    v
                 M4
             Datapoint
                    |
                    v
             M8 ReportRun
                    |
                  FREEZE
                    |
                    v
          FrameworkSnapshot
                    |
              +-----+-----+
              |           |
              v           v
        SnapshotNode  SnapshotNode
              |
              v
       SnapshotMapping
              |
              | frozen datapoint identity
              v
        Value Provider
              |
        +-----+------+
        |            |
        v            v
       M5           future M6
    Captured       Calculated
     Answer          Result
        |            |
        +-----+------+
              |
              v
        ResolvedValue
              |
              v
      Future Reporting
21. What Phase 2 Does NOT Do
Phase 2 does not:

create M5 Answers;

approve M5 submissions;

modify M5 data;

perform emission calculations;

modify M6;

aggregate OrgNode values;

generate PDF;

generate Excel;

create final report templates;

create disclosure tasks;

create narrative answers;

perform regulatory compliance scoring.

Its responsibility is:

Resolve the frozen report mappings against eligible approved source values and expose the result in a deterministic, provenance-preserving reporting contract.

22. Review Hardening — Root Cause
The Phase 2 review identified a historical-identity problem.

The original lookup relied too heavily on the live M4 datapoint code.

This created a scenario where:

M8 freezes:

UUID = A
code = ENERGY_TOTAL
Later:

M4 changes:

UUID = A
code = ENERGY_TOTAL_KWH
If M8 resolves using the live code, the frozen report can stop finding the correct M5 value.

The architectural mistake was:

mutable code
    ↓
used as historical identity
The corrected architecture is:

stable UUID
    ↓
historical operational identity

frozen code
    ↓
historical metadata
23. Review Hardening — Corrected Lookup
Modern snapshots resolve using:

SnapshotMapping.source_datapoint_id
against M5:

DataRequest.datapoint_id
with additional context:

reporting period
company
APPROVED submission
Conceptually:

source_datapoint_id
        +
reporting_period
        +
company
        +
APPROVED
        |
        v
M5 DataRequest
        |
        v
M5 Answer
This makes historical resolution robust against live code changes.

24. Review Regression — M4 Code Rename
A high-value regression scenario is:

1. Create M4 datapoint
2. Create M7 mapping
3. Freeze M8 report
4. Create/approve M5 value
5. Rename live M4 datapoint code
6. Resolve M8 report
7. Verify original approved value is still returned
The test proves that M8 uses source_datapoint_id rather than the mutable live code.

25. Review Regression — Company Isolation
Another regression scenario creates:

Company A
    ENERGY_TOTAL
    FY2025
    value = 100

Company B
    ENERGY_TOTAL
    FY2025
    value = 500
The ReportRun belongs to Company A.

Resolution must produce:

100
and never:

500
This verifies that M8 respects the complete reporting scope.

26. Current M8 Phase 2 Architecture Status
M8 Phase 1 — ReportRun/Snapshot
        COMPLETE

M8 Phase 2 — Approved M5 Value Resolution
        COMPLETE

M5 mutation by M8
        NONE

M6 calculation execution by M8
        NONE

Framework snapshot
        IMMUTABLE

Value resolution
        READ-ONLY

Approved-only filtering
        ENFORCED

Company scope
        ENFORCED

Frozen datapoint identity
        UUID-BASED

Legacy snapshot fallback
        DOCUMENTED

Typed values
        PRESERVED

TABLE structure
        PRESERVED

Provenance
        PRESERVED

M6 provider extension point
        READY
27. Final M8 Mental Model
PHASE 1
========

M3 + M7
   |
   v
ReportRun
   |
 FREEZE
   |
   v
Immutable M8 Snapshot


PHASE 2
========

Immutable M8 Snapshot
   |
   v
Frozen Mapping
   |
   v
Approved M5 source value
   |
   v
ResolvedValue
Or, in one sentence:

M8 freezes what the report is asking for, then resolves the frozen mappings against the correct approved source values without changing those source records.

The most important identity rule is:

Use the frozen source datapoint ID for historical resolution; keep the frozen datapoint code as historical metadata, not as the primary identity.

28. Complete Responsibility Boundary
M4
Canonical Datapoint
       |
       +--------------------+
       |                    |
       v                    v
      M5                   M7
 Data Capture         Framework Mapping
       |                    |
       |                    v
       |              M8 Phase 1
       |              Report Snapshot
       |                    |
       |                    v
       +------------> M8 Phase 2
                    Value Resolution
                           |
                     +-----+-----+
                     |           |
                     v           v
                    M5      future M6
                 captured   calculated
                    values    results
                     |           |
                     +-----+-----+
                           |
                           v
                    Reporting Dataset
                           |
                           v
                 Future Readiness /
                 Rendering / Export
The final architecture principle is:

M7 defines the framework structure and mappings. M8 freezes that structure into a historical snapshot. M5 owns captured answers and approval. M6 owns calculations. M8 resolves eligible source values for the frozen reporting context and exposes a stable reporting-value contract.

29. Engineering Lesson From Phase 2 Review
The most important engineering lesson from this review is:

A historical system must preserve stable identity, not merely mutable labels or codes.

When implementing historical reporting, always ask:

What is the actual identity of this record?

Can that identity change?

What information must remain historically stable?

Which fields are operational identifiers?

Which fields are only display metadata?

What tenant/company scope is required?

What workflow state makes a source record eligible?

What regression test proves the historical behavior?
For M8:

Stable identity
    = source_datapoint_id

Historical metadata
    = canonical_datapoint_code

Tenant scope
    = ReportRun.company

Time scope
    = ReportRun.reporting_period

Eligible workflow state
    = APPROVED

Historical report structure
    = M8 Snapshot

Current source answer
    = M5 approved Answer

Future calculated source
    = M6 provider
This distinction is fundamental to keeping the reporting architecture correct as M5, M6, and future reporting capabilities evolve.