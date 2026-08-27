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
                       |                    |
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

This is a backend-only proof. Frontend capture screens, import handlers,
calculations, framework/report value resolution, and notifications remain
separate follow-up work.

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
separate work.

## Answers Import Integration

M5 Answers can be populated through the M13 `ANSWERS` import handler.

The import reuses the existing M5 `DataRequest`, `Submission`, and `Answer`
models and services. It does not introduce a separate import-specific
Answer model or request/submission lifecycle.

### Imported Answer scope

The production ANSWERS importer supports scalar datapoints:

* `DECIMAL`
* `INTEGER`
* `TEXT`
* `LONG_TEXT`
* `BOOLEAN`
* `SELECT`
* `DATE`

`TABLE` datapoints are intentionally not supported by the current importer.

The ReportingPeriod is supplied as ImportBatch context and is authoritative
for all rows in the workbook.

### DataRequest resolution

For each imported row, M5 resolves the existing DataRequest using:

```text
Datapoint + OrgNode + ReportingPeriod
```

The importer does not create DataRequests, Submissions, campaigns, or other
M5 workflow records.

If no eligible DataRequest exists, the import row is rejected with a
structured validation error.

The existing request metadata remains unchanged, including:

* assignee
* due date
* instructions
* campaign linkage
* lifecycle state

### Submission and DRAFT behavior

Imported values may populate only the current editable `DRAFT` Submission
belonging to an eligible `OPEN` DataRequest.

The importer cannot populate:

* submitted submissions;
* approved submissions;
* rejected or otherwise non-editable submissions.

Importing an Answer never automatically:

* submits the Submission;
* approves the Submission;
* rejects the Submission;
* bypasses reviewer workflow.

After import, the draft continues through the normal M5 submission and
review lifecycle.

### Canonical datapoint and unit resolution

Imported `datapoint_code` values resolve to the active canonical M4
Datapoint.

The datapoint definition remains authoritative for:

* datapoint type;
* validation metadata;
* UnitFamily;
* supported value semantics.

When a datapoint requires a UnitFamily, the supplied `unit_code` must resolve
to an active canonical M4 Unit belonging to that UnitFamily.

Units are not recreated or defined by the importer.

### Typed Answer behavior

Imported values are normalized and stored using the existing M5 typed-value
semantics.

The importer supports the canonical scalar types defined above and
performs type-specific validation before commit.

SELECT values must resolve to an active registered option for the target
datapoint.

BOOLEAN and DATE values use the deterministic parsing rules defined by the
production ANSWERS import contract.

Existing M5 validation remains authoritative for submit-time completeness,
required evidence, and other workflow requirements.

### Validation versus commit

Import validation is read-only with respect to M5 destination records.

During validation:

* no Answer is created;
* no existing Answer is updated;
* no DataRequest is created;
* no Submission is created;
* lifecycle and authorization rules are checked.

Only after successful M13 batch validation can the import commit.

During commit, mutable M5 state is revalidated before the Answer is created
or updated.

Answer persistence uses the existing M5 draft-save/domain-service path.

### Authorization and OrgNode scope

Answers imported through M13 remain subject to the existing M5/RBAC
authorization rules.

A maker may import only when:

1. the maker is assigned to the target DataRequest; and
2. the maker has the required `data.enter` capability for the target
   OrgNode.

An authorized manager may import only where the existing `data.manage`
contract permits the target OrgNode.

Permission and OrgNode scope must come from the same qualifying
`UserRoleAssignment`. Unrelated assignments must not be combined to grant
access.

Knowing an OrgNode UUID or code does not grant permission to write to that
scope.

Authorization is checked during validation and rechecked during commit
where mutable authorization state may have changed.

### Update and idempotency

The canonical M5 request context is:

```text
Datapoint + OrgNode + ReportingPeriod
```

A later import for an existing editable draft Answer updates the existing
draft through the supported M5 draft-save semantics rather than creating a
duplicate Answer.

Submitted or approved historical Answers are never rewritten by the
importer.

The same M13 ImportBatch cannot be committed more than once.

Duplicate target rows within a single workbook are rejected during
validation.

### Import provenance

Imported Answers remain traceable to the M13 import that created or last
populated them.

The provenance contract identifies the originating:

* ImportBatch;
* ImportRow;
* source workbook;
* original Excel row number;
* importing user.

The entire spreadsheet row is not stored as opaque JSON on the M5 Answer.

This allows an imported draft Answer to be traced back to the workbook,
batch, and source row that populated it.

### TABLE import limitation

TABLE datapoints are deliberately rejected by the production ANSWERS
importer.

TABLE import is deferred because it requires a separate spreadsheet
contract for:

* table rows;
* dynamic rows;
* columns;
* typed cells;
* row identity;
* display order;
* required cells;
* minimum-row validation.

A future implementation must use the existing M5 `AnswerTableRow` and
`AnswerTableCell` domain rather than introducing a parallel import-specific
table model.

### Import API relationship

The ANSWERS importer uses the existing M13 import APIs:

```text
POST /api/imports/batches/
POST /api/imports/batches/{id}/validate/
GET  /api/imports/batches/{id}/rows/
POST /api/imports/batches/{id}/commit/
```

After a successful commit, the resulting Answer is part of the normal M5
DataRequest → Submission → Answer workflow and is exposed through the normal
M5 Data Capture APIs.

No separate Answers upload API or import-specific Answer store is required.
