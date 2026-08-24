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
