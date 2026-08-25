# Goals, KPIs and Targets (M10)

M10 is the planning layer: `Goal -> KPI -> Target`, with lightweight KPI
Initiatives. It does not own ESG source values or create M5 answers.

## Materiality is optional

Goals can be created independently. `material_topic`, `material_subtopic`, and
`source_assessment_topic` are nullable provenance/context links. Their deletion
sets the link to null, preserving the Goal, KPI and Target records. A later
association does not recreate planning identities.

## Metric and target contract

KPIs use `DATAPOINT`, `CALCULATED_METRIC`, or `MANUAL_REFERENCE` metric
sources. A `DATAPOINT` KPI references one active numeric M4 Datapoint and uses
only explicit `SUM`, `AVG`, `LATEST`, `COUNT`, or `NONE` aggregation. The M5
provider includes only `APPROVED` submissions; missing data returns `NO_DATA`,
not zero. `CALCULATED_METRIC` intentionally has a provider boundary for future
M6 integration rather than a dependency on unfinished calculation internals.

Targets freeze baseline and endpoint values/units and link ReportingPeriods.
Baseline must precede endpoint; units must be active and from the KPI family.
The MVP trajectory is linear interpolation by reporting-period year. Progress
returns approved actual, trajectory, variance, percentage where meaningful and
`AHEAD`, `ON_TRACK`, `BEHIND`, or `NO_DATA`.

`KPIInitiative` is planning-only: name, comments, optional OrgNode/owner, due
date, `PLANNED|ONGOING|COMPLETE|PARKED`, and 0–100 anticipated impact.

## API and authorization

All routes are session-authenticated under `/api/targets/`: goals, nested KPI
and target collections, target progress, and KPI initiatives. `target.set` is
required for the current M10 read/write slice. Target/initiative detail and
mutations scope the OrgNode through the *same* qualifying `UserRoleAssignment`
that grants `target.set`; out-of-scope objects return 404. Superusers retain
platform-wide behavior.

The frontend provides `/goals` and `/goals/:id`: independent goal creation,
KPI tabs, baseline/target configuration, actual/trajectory/target chart and
initiative creation. It does not fabricate projected values.

## Deferred

Calculated-provider registration, automated campaign generation, SBTi/scenario
pathways, benchmark acquisition, notifications, evidence and target-specific
project management remain outside M10 foundation.
