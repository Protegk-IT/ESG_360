# Goals, KPIs and Targets (M10)

M10 is the planning layer: `Company -> Goal -> KPI -> Target`, with lightweight
KPI Initiatives. It does not own ESG source values or create M5 answers.

Every new Goal has an explicit Company context. KPIs, Targets and Initiatives
inherit that tenant context through their Goal; an OrgNode selected for a
Target or Initiative must belong to that Company. The corrective migration
keeps pre-existing Goals nullable for upgrade safety. A legacy company-wide
Goal with no Company deliberately resolves no actuals rather than risking a
cross-company aggregate.

Migration `targets.0003` backfills an existing Goal only when its Company is
deterministic: all scoped Target/Initiative OrgNodes identify one Company, its
AssessmentTopic provenance identifies one assessment Company, or the database
has exactly one active Company. Conflicting evidence remains null for an
explicit later assignment; the migration never guesses across tenants.

## Materiality is optional

Goals can be created independently. `material_topic`, `material_subtopic`, and
`source_assessment_topic` are nullable provenance/context links. Their deletion
sets the link to null, preserving the Goal, KPI and Target records. A later
association does not recreate planning identities.

The Goal write contract validates that a selected subtopic belongs to its Topic
and that an `AssessmentTopic` provenance record matches both. Selecting an
assessment topic through the frontend derives the matching reusable Topic and
Subtopic; changing a Topic clears incompatible nested context rather than
silently retaining it. Removing all three links restores a fully independent
Goal without changing its KPI or Target IDs.

## Metric and target contract

KPIs use `DATAPOINT`, `CALCULATED_METRIC`, or `MANUAL_REFERENCE` metric
sources. A `DATAPOINT` KPI references one active numeric M4 Datapoint and uses
only explicit `SUM`, `AVG`, `LATEST`, `COUNT`, or `NONE` aggregation. The M5
provider includes only `APPROVED` submissions from the Goal's Company;
`DRAFT`, `SUBMITTED`, and `REJECTED` answers never contribute. `COUNT` with no
approved answers is `NO_DATA`; `NONE` requires exactly one approved value or
returns an explicit ambiguity state; `LATEST` uses `Submission.approved_at`
with deterministic UUID tie-breaks. Numeric aggregates and progress normalize
through the canonical M4 Unit family before arithmetic. `CALCULATED_METRIC`
intentionally has a provider boundary for future M6 integration rather than a
dependency on unfinished calculation internals.

Targets freeze baseline and endpoint values/units and link ReportingPeriods.
Baseline must precede endpoint and both periods are ANNUAL in the current MVP;
units must be active and from the KPI family. `REFERENCE` permits a manual
baseline with source/provenance. `SYSTEM_DATA` freezes the matching approved
M5 value server-side, so a caller cannot enter an arbitrary value and label it
system data. `REDUCE` endpoints cannot increase, `INCREASE` endpoints cannot
decrease, and `MAINTAIN` endpoints equal their baseline. Only one DRAFT/ACTIVE
target may exist per KPI plus OrgNode scope (or per company-wide KPI), avoiding
ambiguous overlapping planning windows. ACHIEVED, MISSED and RETIRED targets
are immutable historical records.
The MVP trajectory is linear interpolation by reporting-period year. Progress
returns approved actual, trajectory, variance, percentage where meaningful and
`AHEAD`, `ON_TRACK`, `BEHIND`, or `NO_DATA`.

`KPIInitiative` is planning-only: name, comments, optional OrgNode/owner, due
date, `PLANNED|ONGOING|COMPLETE|PARKED`, and 0–100 anticipated impact.
Initiatives are created through `/kpis/{kpi_id}/initiatives/`; the URL owns the
KPI association, and a PATCH cannot move an Initiative to another KPI/Goal.

## API and authorization

All routes are session-authenticated under `/api/targets/`: goals, nested KPI
and target collections, target progress, and KPI initiatives. `target.view`
provides read-only access; `target.set` provides scoped planning writes and
also permits reads. Target/initiative detail and mutations scope the OrgNode
through the *same* qualifying `UserRoleAssignment` that grants `target.set`;
out-of-scope objects return 404. A `target.view` scope can only grant reads,
never writes. Superusers retain platform-wide behavior.

Goals and KPIs intentionally have no OrgNode before their first Target. A
scoped setter may see and configure only the setup records it created until a
Target exists. From that point onward, access is derived only from the actual
Target/Initiative OrgNode scope. Company-wide Targets and Initiatives require a
company-wide `target.set` assignment; a site-scoped setter cannot create them.
List/detail responses include a server-calculated `can_manage` capability. The
frontend uses it for record mutation controls rather than assuming a global
`target.set` permission grants every visible resource.

Goal creation follows the same boundary: a scoped `target.set` user can choose
only a Company represented by its own qualifying `target.set` OrgNode
assignments. A company-wide assignment and superuser retain the platform-wide
creation contract. An unrelated role/scope cannot be combined to select a
different Company.

Routes are:

- `GET/POST /api/targets/goals/`, `GET/PATCH /api/targets/goals/{goal_id}/`
- `GET/POST /api/targets/goals/{goal_id}/kpis/`,
  `GET/PATCH /api/targets/kpis/{kpi_id}/`
- `GET/POST /api/targets/kpis/{kpi_id}/targets/`,
  `GET/PATCH /api/targets/targets/{target_id}/`, and
  `GET /api/targets/targets/{target_id}/progress/`
- `GET/POST /api/targets/kpis/{kpi_id}/initiatives/` and
  `GET/PATCH /api/targets/initiatives/{initiative_id}/`

The frontend provides `/goals` and `/goals/:id`: an add/edit Goal dialog with
optional Materiality provenance and readable owner/status selectors, KPI tabs,
baseline/target configuration, actual/trajectory/target chart, plus a compact
KPI-specific Initiative manager. The manager preserves the selected Goal/KPI,
lists Initiative owner/scope/status/due date/impact, and supports create/edit
without turning planning records into project-management tasks. It does not
fabricate projected values.

## Local visual-test fixture

`python manage.py seed_m10_demo` is a repeat-safe development fixture. It
does not reset the database or alter user-created planning records. It reuses
the active company/root hierarchy where available and creates clearly named
`DEMO M10` periods, facility, users, goals and targets. Its M10 actuals are
real M5 `DataRequest -> draft answer -> submit -> approve` records, rather
than values written into M10. The fixture includes Water Stewardship with
multiple KPI tabs, Energy Efficiency, Renewable Energy Adoption, and an
independent Operational Waste Reduction goal with no Materiality link.
The command never overwrites an existing M4 Datapoint definition: it reuses a
compatible canonical code, and fails clearly if an existing definition has
incompatible type, module, collection-level, unit-family or default-unit
semantics.

## Deferred

Calculated-provider registration, automated campaign generation, SBTi/scenario
pathways, benchmark acquisition, notifications, evidence and target-specific
project management remain outside M10 foundation.
