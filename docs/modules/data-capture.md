# Data Capture (M5)

M5 is the generic, datapoint-driven capture backbone. It records operational

ESG data once for downstream calculation, framework mapping, and reporting;

it does not define Energy-, Water-, Waste-, or framework-specific answer

models. M4 remains the source of truth for what a datapoint means.

## Domain model

```text

M4 Datapoint + OrgNode + ReportingPeriod

  -> DataRequest (assignee, due date, derived module code)

       -> Submission (one current workflow per request)

            -> Answer (typed scalar or TABLE container)

                 -> AnswerTableRow -> AnswerTableCell

            -> EvidenceFile

            -> SubmissionEvent (append-only)

  -> DataRequestEvent (append-only assignment history)

```

`DataRequest` represents an operational obligation, for example: *Site A owes

the canonical energy-consumption datapoint for FY 2026 Q1*. It is distinct from

the future M8 disclosure-assignment model. It stores the canonical datapoint,

OrgNode, ReportingPeriod, assignee, requester, due date, and a `module_code`

that is always derived from the M4 datapoint's Module Registry relationship.

Each request has exactly one current `Submission`. Reopen/resubmit keeps that

same submission and appends workflow events instead of destroying history or

creating an untraceable replacement.

## Typed values

`Answer` and `AnswerTableCell` use separate queryable fields:

```text

decimal_value | integer_value | text_value | boolean_value

selected_option | date_value | unit

```

Only the field matching the M4 definition's data type may be populated. A

draft may leave all value fields empty, but a supplied value is always checked

against its definition. The active M4 metadata contract interpreted by M5 is:

| Definition type | Supported metadata |

| --- | --- |

| `DECIMAL`, `INTEGER` | `min`, `max` |

| `DECIMAL` | `decimal_places` (meaningful fractional digits; stored trailing zeroes do not count) |

| `TEXT`, `LONG_TEXT` | `max_length` |

| `TABLE` | `min_rows` |

Other JSON keys remain M4 metadata but are not treated as executable M5 rules

until their meaning is added to the accepted M4 contract.

Numeric values with a declared UnitFamily require an active Unit from that

family. The lifecycle service applies the M4 `default_unit` when a numeric

value is saved without an explicit unit; an inactive default unit is rejected

like any other inactive unit. Numeric definitions without a UnitFamily reject a

unit. `SELECT` values must be active `DatapointOption` records belonging to the

datapoint.

No arbitrary JSON answer-value field exists.

## TABLE answers

M4 owns a TABLE definition's `DatapointTableColumn` and optional fixed

`DatapointTableRow` records. M5 stores entered values as normalized rows and

cells:

- `AnswerTableRow.definition_row` points to the canonical fixed row when one

  exists. A fixed row can occur once per answer and uses the catalog label.

- A row with no `definition_row` is a user-added dynamic row. It is permitted

  only when `Datapoint.allow_dynamic_rows` is true and must have a label.

- `AnswerTableCell.column` must belong to the answer's TABLE datapoint, and a

  row can have one cell for each column.

Each cell uses the same typed-value and metadata validation as a scalar answer,

with its M4 column as the definition. Required cells must contain a complete,

typed value at submission—not merely exist as an empty cell. The current M4

catalog does not model a separate option list for `SELECT` TABLE columns:

`DatapointOption` can only belong to a `SELECT` datapoint, while TABLE columns

belong to a TABLE datapoint. M5 therefore rejects supplied values for such a

column rather than accepting an invented option source; adding a canonical M4

table-column option contract is a prerequisite for supporting that combination.

On submission, a required datapoint needs a complete answer. An optional empty

datapoint may be submitted without one. Once a TABLE has rows, all configured

fixed rows must exist; required columns must have complete cells, and

`validation_metadata.min_rows` is respected when present. Fixed rows are

canonicalized to their M4 labels and display order. Database uniqueness

constraints prevent a repeated fixed row, repeated row order, or repeated cell

for a row/column; cross-definition type checks remain in the domain validator

because the type lives on the related M4 definition. Nested tables are not

supported by the M4/M5 contract.

## Lifecycle

```text

DRAFT --submit--> SUBMITTED --approve--> APPROVED

                       |                    |

                       +--reject--> REJECTED +--reopen--> DRAFT

                                      |

                                      +--reopen--> DRAFT

```

The persisted submission statuses are `DRAFT`, `SUBMITTED`, `APPROVED`, and

`REJECTED`. Reopen is a controlled transition back to `DRAFT`, recorded as a

`REOPENED` event rather than an ambiguous additional status.

All lifecycle and draft operations are in

`apps.data_capture.services.lifecycle.DataCaptureLifecycleService` and execute

inside database transactions with submission row locking. Direct status changes

are rejected by the model.

- Only the currently assigned user may save a draft answer/table row or submit.

- Drafts may be incomplete; `submit` performs completeness validation.

- Approval and rejection require `SUBMITTED`; the original submitter cannot

  approve or reject their own submission.

- Rejection and reopen both require a non-empty reason. The last rejection

  reason remains on the submission and the full historical reason is preserved

  in the immutable event stream.

- Approval marks the related request `COMPLETED`; reopening returns it to

  `OPEN`.

- All M5 writes and transitions reject a ReportingPeriod that is not `OPEN`.

The session-authenticated API applies canonical `data.enter`, `data.submit`,

`data.approve`, and `data.manage` permissions with OrgNode scoping according

to the Identity contract. The domain service remains authoritative for the

non-negotiable assignee/maker and maker-checker invariants.

## Evidence foundation

`EvidenceFile` uses a Django `FileField` (not a hard-coded local path) and is

always attached to a submission, optionally to its answer. It records original

filename, content type, byte size, and uploader. The foundation accepts PDF,

PNG, JPEG, CSV, and XLSX files up to 10 MB; an answer attachment must belong to

the same submission. The authenticated evidence API and its draft-only

lifecycle rules are documented below.

## Current service entry points

The initial internal domain API is:

```python

DataCaptureLifecycleService.create_request(...)

DataCaptureLifecycleService.reassign_request(...)

DataCaptureLifecycleService.save_scalar_answer(...)

DataCaptureLifecycleService.save_table_row(...)

DataCaptureLifecycleService.submit(...)

DataCaptureLifecycleService.approve(...)

DataCaptureLifecycleService.reject(...)

DataCaptureLifecycleService.reopen(...)

```

The current API pass exposes these operations through session-authenticated,

CSRF-protected, RBAC-scoped endpoints using the existing Core error envelope.

Calculation, imports, framework resolution, reporting, frontend capture

screens, and other downstream modules must consume this domain rather than

create parallel answer stores.

## API and scoped authorization

All M5 endpoints are session-authenticated below `/api/data-capture/`; unsafe

requests require the normal Django CSRF token. Successful responses use the

Core envelope (`{"success": true, "message": "…", "data": …}`), while

handled validation, permission, and not-found errors use the shared error

envelope described in `docs/contracts/core-api.md`.

Request and evidence collection responses are paginated inside `data` with

`count`, `next`, `previous`, and `results`. They default to 25 records; callers

may set `?page=` and `?page_size=` up to 100.

| Method and path | Capability | Purpose |

| --- | --- | --- |

| `GET /requests/` | any relevant `data.*` capability | Scoped requests the current user may read. |

| `POST /requests/` | `data.manage` | Create a request for an OrgNode in the matching assignment scope. |

| `GET /requests/mine/` | `data.enter` / `data.submit` or a read capability | Current user's assigned scoped requests. |

| `GET /requests/{id}/` | any relevant `data.*` capability | Scoped request detail. |

| `POST /requests/{id}/reassign/` | `data.manage` | Reassign an open draft request. |

| `GET /requests/{id}/submission/` | scoped read | Current submission and normalized answer. |

| `PATCH /requests/{id}/submission/answer/` | `data.enter` | Save one scalar draft value. |

| `POST /requests/{id}/submission/table-rows/` | `data.enter` | Create/save a normalized TABLE row and cells. |

| `PATCH /requests/{id}/submission/table-rows/{rowId}/` | `data.enter` | Update an existing normalized TABLE row/cells. |

| `GET /requests/{id}/submission/history/` | scoped read | Immutable request and submission events. |

| `POST /requests/{id}/submission/submit/` | `data.submit` | Submit the assigned user's valid draft. |

| `POST /requests/{id}/submission/approve/` | `data.approve` | Approve a submitted request. |

| `POST /requests/{id}/submission/reject/` | `data.approve` | Reject a submitted request; requires `reason`. |

| `POST /requests/{id}/submission/reopen/` | `data.approve` | Reopen an approved/rejected request; requires `reason`. |

| `GET /requests/{id}/evidence/` | `evidence.view` | Scoped evidence metadata for the request submission. |

| `POST /requests/{id}/evidence/` | `evidence.upload` | Upload draft evidence, optionally linked to its submission answer. |

| `GET /requests/{id}/evidence/{evidenceId}/` | `evidence.view` | Scoped evidence metadata. |

| `GET /requests/{id}/evidence/{evidenceId}/download/` | `evidence.view` | Authenticated storage-backed download. |

| `DELETE /requests/{id}/evidence/{evidenceId}/` | `evidence.upload` | Remove draft evidence as the assigned maker. |

`data.manage` is the canonical request-administration capability added for

M5. It is assigned to the existing Company Admin and ESG Manager role bundles.

It deliberately does not imply `data.enter`, `data.submit`, or `data.approve`.

The existing Data Entry bundle retains `data.enter` and `data.submit`; the

existing Reviewer bundle retains `data.approve`.

### Scope boundary

Every request query resolves its `OrgNode` through qualifying

`UserRoleAssignment` records. The implementation evaluates each permission

and its role assignment scope together. A user who has `data.enter` at Site A

and `data.approve` at Site B can enter their assigned request at A and review

at B, but cannot approve at A. Capture users only see their own assigned

requests for `data.enter`/`data.submit`; managers and reviewers can see all

requests in the scope of their `data.manage`/`data.approve` assignment.

Detail and action lookups apply the same scoped queryset. A request outside a

qualifying scope is returned as a 404, rather than a 403 that reveals its

existence. Superusers retain platform-wide access. The API authorization is

authoritative; future UI visibility is not a security control.

When creating or reassigning, M5 also verifies that the assignee is active and

has one active `UserRoleAssignment` whose role grants both `data.enter` and

`data.submit`, whose module is unrestricted or `data`, and whose OrgNode scope

covers the request. This prevents assigning a request to an arbitrary user or

combining entry capability from one assignment with submit/scope from another.

### Write examples

Create a request (a `data.manage` assignment must cover the target OrgNode):

```json

POST /api/data-capture/requests/

{

  "datapoint": "4c2f…",

  "org_node": "895e…",

  "reporting_period": "d13a…",

  "assignee": 17,

  "due_date": "2027-06-15",

  "instructions": "Use the monthly utility invoice."

}

```

Save a scalar draft. The serializer only transports typed fields; M5's domain

validator chooses the one field valid for the datapoint and returns useful M4

validation errors when it does not match.

```json

PATCH /api/data-capture/requests/{id}/submission/answer/

{"decimal_value": "1250.5000", "unit": "7da1…"}

```

Save a fixed TABLE row. A dynamic row omits `definition_row` and is accepted

only when the M4 datapoint permits dynamic rows.

```json

POST /api/data-capture/requests/{id}/submission/table-rows/

{

  "definition_row": "f118…",

  "display_order": 1,

  "cells": [

    {"column": "c111…", "text_value": "Grid electricity"},

    {"column": "c112…", "decimal_value": "1250", "unit": "7da1…"}

  ]

}

```

`status`, approver fields, and workflow timestamps are not writable through a

generic serializer. Submit, approve, reject, and reopen call the transactional

`DataCaptureLifecycleService`, which remains the sole state-transition path.

## Evidence files

Evidence belongs to a `Submission` and may optionally point at its scalar or

TABLE-container `Answer`. The answer association is validated server-side and

cannot point at another submission. Evidence is not an independent storage or

scope domain: every evidence endpoint resolves the parent DataRequest and its

OrgNode using the same `UserRoleAssignment` scoping rules as M5.

`evidence.view` governs metadata/download and `evidence.upload` governs

upload/delete. The permission's own module/scope assignment must cover the

request OrgNode; out-of-scope request or evidence UUIDs return 404. Upload and

delete additionally use the M5 domain maker rule, so the currently assigned

user is the only user who may change evidence. Superusers bypass RBAC and

OrgNode scope consistently with the platform, but do not bypass the domain's

maker/checker separation for draft mutation.

Evidence mutation is draft-only and respects ReportingPeriod locking. A

submitted, approved, or rejected submission may be read but cannot receive or

lose evidence. It must first follow the normal reopen-to-draft lifecycle.

The API accepts PDF, PNG, JPEG, CSV, and XLSX files up to 10 MB. It derives

the recorded content type from server-read signatures/structure (or UTF-8 CSV

content), uses the uploaded file's measured size, strips path components from

the original filename, and stores the file through Django's configured

`FileField` storage. Metadata responses deliberately omit the storage path;

download streams the file only through the authenticated application route.

Deleting draft evidence writes the normal Core audit record without file

contents or storage path and removes the storage object only after the database

transaction commits.

Example multipart upload:

```text

POST /api/data-capture/requests/{id}/evidence/

Content-Type: multipart/form-data

file=@meter-invoice.pdf

answer={optional-answer-uuid}

```

## Backend vertical slice

The automated M5 vertical-slice test now proves this workflow with separate

scoped users: a `data.manage` manager creates scalar and TABLE requests at a

site; the assigned `data.enter`/`data.submit` maker retrieves the request,

saves a scalar draft and a fixed normalized TABLE row/cell, uploads evidence,

and reloads submission/evidence metadata. The maker submits; a separate

`data.approve` reviewer rejects with a reason, reopens, and finally approves

the resubmission. The immutable submission history retains every transition.

The frontend now consumes this existing M5 domain through the shared React/Vite
application shell, AuthContext, API client, M4 DynamicFieldRenderer, and the
normalized M5 table/evidence/lifecycle endpoints documented below. Frontend
work does not introduce parallel answer storage, authentication, lifecycle, or
permission models. Import handlers, calculations, framework/report value
resolution, notifications, and downstream reporting remain separate work.

## Frontend M5 handover

Routes and screens

The M5 frontend is implemented in the existing application shell. The main
screens/routes are:

Route

Screen

Capability intent

/data-capture

Data Capture workspace/request list

Browse M5 requests available to the current user.

/data-capture/requests/{requestId}

Data Capture request workspace

Request details, data entry, draft save/resume, evidence, history, and lifecycle actions when permitted.

/data-capture/requests/create

Create Data Request

Manager request creation using data.manage.

/data-capture/manage

Manage Requests

Manager request administration queue.

/data-capture/manage/{requestId}

Manage Request Detail

Manager inspection and reassignment.

/data-capture/review

Review Requests

Reviewer queue for submitted work.

Data Capture navigation remains separate from M4 Datapoint Catalog administration
and uses the existing layout/sidebar, AuthContext, shared ProtectedRoute, and
shared API client. No parallel application shell or authentication system is
introduced.

Scalar typed-write adapter

The request workspace consumes the accepted M4 DynamicFieldRenderer for
DECIMAL, INTEGER, TEXT, LONG_TEXT, BOOLEAN, SELECT, and DATE. Renderer
state is converted to the exact M5 typed answer fields rather than a generic
JSON value. Existing answer units are preserved during hydration and save, and
numeric unit metadata is resolved from the M4 datapoint definition. Backend
validation remains authoritative for field type, range, options, and units.

Normalized TABLE transport

TABLE values use normalized M5 AnswerTableRow and AnswerTableCell records. The
frontend adapter preserves fixed-row definition_row UUIDs, dynamic row labels and
display order, cell column UUIDs, typed cell fields, and unit UUIDs where
applicable. The entire TABLE is never serialized as opaque JSON.

Saved rows are hydrated against the M4 fixed-row and column definitions so missing
fixed rows/cells are recreated without losing persisted identities. Dynamic rows are
kept separate from fixed rows and are only available when
allow_dynamic_rows is enabled. Persisted dynamic-row removal is sent through the
M5 table-row delete operation; fixed canonical rows are never removed through that
path. M4's current limitation for SELECT TABLE columns remains unchanged: no
invented option catalog is introduced.

Draft save and resume

DRAFT is the editable state. Save/submit use the scalar or normalized TABLE
adapter and then refresh the request so persisted server state is authoritative.
Reloading a draft restores primitive values, units, TABLE row/column identity, and
persisted dynamic rows. Backend field/table validation errors are surfaced in the
workspace where available and otherwise use the shared API error parser.

Evidence flow

The frontend uses authenticated M5 evidence endpoints for upload, list, download,
and delete. Upload uses multipart/form-data; supported PDF, JPEG, PNG, CSV, and
XLSX files are client-checked against the 10 MB limit before submission. Downloads
use the authenticated application endpoint rather than direct storage/media URLs.
Delete is exposed only while draft mutation is permitted. Backend lifecycle, file
validation, answer association, and OrgNode scope remain authoritative.

Lifecycle/action mapping

The frontend maps directly to the persisted M5 lifecycle:

DRAFT -> SUBMITTED -> APPROVED

SUBMITTED -> REJECTED -> DRAFT

and uses the backend-supported reopen transition where allowed. The request workspace
calls the existing submit, approve, reject, and reopen endpoints; it never changes
workflow status locally as a substitute for a server transition. Reject and reopen
require a reason in the UI. Submitted/approved/rejected work is treated as
non-editable until the backend-supported lifecycle returns it to draft.

Permission-aware UX

General route/navigation visibility uses the existing AuthContext permission list.
Request-level actions use the centralized data-capture access logic and should
consider assignee identity, lifecycle state, permission, and OrgNode scope.
Maker actions use data.enter/data.submit; evidence uses evidence.view and
evidence.upload; reviewer actions use data.approve; manager actions use
data.manage. No new M5 permission code is introduced.

The frontend does not replace backend authorization. In particular, permission and
OrgNode scope must be evaluated from the same qualifying assignment; the UI must not
combine a permission from one assignment with the scope of another. When the
frontend lacks sufficient assignment reference data, request-specific action checks
fail closed rather than granting authority from the flat permission union. Protected
backend 404/403 behavior remains authoritative.

Browser/runtime verification

The frontend acceptance flow should be verified with separate real users and
scopes:

Create a request for a canonical datapoint, OrgNode, reporting period, and
eligible assignee.

Maker opens the assigned request, enters a primitive value, saves a partial
draft, reloads, and verifies value and unit persistence.

Maker edits fixed and dynamic TABLE rows, saves, reloads, removes a persisted
dynamic row when permitted, saves again, and verifies it stays removed after
reload.

Maker uploads, lists, downloads, and deletes evidence while the request remains
editable.

Maker submits and verifies normal draft mutation disappears.

Reviewer rejects with a reason, reopens with a reason, maker corrects and
resubmits, and reviewer approves.

Verify immutable request/submission history shows the workflow events and reasons.

Verify a user with different Role+OrgNode assignments cannot receive action
controls merely because a permission exists elsewhere in the user's flat
permission list.

Verify out-of-scope direct request access follows the backend's protected
404/403 behavior.

Smoke-test login/session plus Datapoint Catalog, Organization, Reporting
Periods, Materiality, sidebar, and existing routes.

Known limitations

M4 does not currently provide a canonical option catalog for SELECT TABLE columns.

Campaign orchestration APIs exist in M5, but campaign UI is outside this frontend
slice.

Full client-side permission-to-assignment-to-OrgNode reconstruction depends on
the reference data exposed to the authenticated user; backend authorization is
the security boundary for every protected mutation.

Notifications, generic imports, calculations, framework/report value resolution,
and downstream reporting are outside this frontend slice.

Verification commands

Run from frontend/:

npm ci
npm run build
npm run lint
git diff --check

Build output may include existing Vite advisories such as the
vite-tsconfig-paths replacement notice and large-chunk warning; these are
non-blocking warnings rather than M5 lint or TypeScript failures.

## Collection campaigns (M5 orchestration)

`CollectionCampaign` is a manager-facing orchestration record for one

Company and ReportingPeriod. It stores a stable code/name, default due date and

instructions, creator, and a small `DRAFT → ACTIVE → CLOSED` operational

state. It does **not** own capture values, review status, or a second

lifecycle.

Each explicit `CampaignTarget` records exactly one

`Datapoint × OrgNode × intended assignee` mapping and links to the resulting

normal `DataRequest`. The target retains the resolved due date/instructions and

whether its request was `CREATED` or was an `EXISTING` equivalent request. A

target is unique per campaign/datapoint/OrgNode; `DataRequest` retains its

platform-wide uniqueness of datapoint/OrgNode/ReportingPeriod.

### Generation contract

`CollectionCampaignService.generate_requests(campaign, actor, targets)` takes

an explicit list of target objects, not hidden module/category expansion. Each

target supplies canonical M4 datapoint, OrgNode, assignee, and optional due

date/instructions. Before writing anything it validates the complete set:

- campaign period is `OPEN` and campaign is not closed;

- target OrgNodes are active and belong to the campaign Company;

- datapoints are active and their M4 `collection_level` matches the target:

  `ORG_NODE`/`ANY` permit any active node, `FACILITY` requires a facility, and

  `COMPANY` requires the Company root legal-entity node;

- the assignee is active and has one M5-capture assignment granting both

  `data.enter` and `data.submit` over the target node;

- the calling manager has `data.manage` over **each** target node through the

  same qualifying assignment/scope semantics as normal M5 request operations.

The prevalidation and request/link writes run in one transaction. Thus a bad

target leaves no partially generated campaign. New requests are created by the

existing `DataCaptureLifecycleService.create_request`, which derives the

canonical module code and creates the normal draft submission/events.

Generation is replay-safe. Repeating an identical target set returns linked

targets as `replayed` and creates no duplicate requests. If the unique M5

request already exists outside the campaign, the service links it as

`EXISTING`; it never changes that request's assignee, due date, instructions or

lifecycle. A different value for an existing campaign target is rejected:

use controlled reassignment instead of treating generation as an implicit

update.

### Progress and reassignment

Campaign progress is a single aggregate query over linked M5 request and

submission state. It reports target/link totals, `OPEN`/`COMPLETED`/`CANCELLED`

request counts, each submission status, requests without a submission, and

open requests past their due date. Campaigns do not persist duplicated progress

or submission fields.

`bulk_reassign` only accepts selected generated targets that are all open,

draft requests. It prevalidates manager scope and new-assignee eligibility for

every target, then calls the existing M5 reassignment service for every request

inside one transaction. This preserves immutable `DataRequestEvent` history;

it cannot silently move a submitted/approved request or leave half a batch

reassigned. A locked/closed ReportingPeriod blocks both generation and bulk

reassignment. Closing a campaign prevents later generation/reassignment but

does not alter the linked M5 workflow records.

Campaign events are append-only and record campaign creation, generation

summary, bulk reassignment summary, and closure. They complement rather than

replace the normal per-request and per-submission event streams.

### Campaign API

All endpoints are session-authenticated and use the normal CSRF/Core envelopes.

They require canonical `data.manage`; no new permission is introduced.

| Method and path | Purpose |

| --- | --- |

| `GET /campaigns/` | Paginated manager-scoped campaign list. |

| `POST /campaigns/` | Create campaign metadata for a Company/open period. |

| `GET /campaigns/{id}/` | Campaign metadata, only targets in the manager's own scope, and campaign events. |

| `GET /campaigns/{id}/targets/` | Paginated scoped target/request links. |

| `POST /campaigns/{id}/generate/` | Atomically submit explicit targets and create/link normal M5 requests. |

| `GET /campaigns/{id}/progress/` | Aggregate scoped progress. |

| `POST /campaigns/{id}/bulk-reassign/` | Transactional reassignment for explicit target UUIDs. |

| `POST /campaigns/{id}/close/` | Close a fully manageable campaign. |

Example generation request:

```json

POST /api/data-capture/campaigns/{campaignId}/generate/

{

  "targets": [

    {

      "datapoint": "a1b2…",

      "org_node": "c3d4…",

      "assignee": 17,

      "due_date": "2027-06-15",

      "instructions": "Use the signed facility utility invoice."

    }

  ]

}

```

Campaign reads expose only the target rows that the manager's own

`data.manage` assignments cover. A user cannot combine an assignment at Site A

with another role at Site B to generate, inspect, or reassign Site B targets.

The campaign API is backend-only in this issue; campaign UI, reminders,

notifications, spreadsheets/imports, calculations, and reporting remain

separate work
