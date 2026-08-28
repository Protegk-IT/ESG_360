# M13 — Import Batch Foundation

## 1. Purpose

The M13 Import Batch Foundation provides reusable infrastructure for spreadsheet-based imports in ESG_360.

It handles:

* Excel upload and Django storage
* XLSX parsing
* Import batch and row creation
* Row-level validation
* Error tracking
* Revalidation
* Preview pagination and filtering
* Transaction-safe commit
* Import lifecycle tracking
* Activity logging

Domain-specific validation and destination writes are handled by `ImportHandler` implementations.

---

## 2. Supported Import Types

```text
ANSWERS
DATAPOINTS
FRAMEWORK_NODES
STAKEHOLDERS
EMISSION_FACTORS
```

These values define supported import categories. A handler must be registered before an import can be validated or committed.

`FakeAnswersImportHandler` is test-only and is not registered during production startup.

---

## 3. Architecture

```text
XLSX File
   |
   v
ImportUploadService
   |
   +--> Django Storage
   |
   +--> ExcelParser
   |
   v
ImportBatch + ImportRow
   |
   v
ImportBatchService
   |
   v
ImportHandlerRegistry
   |
   v
Domain ImportHandler
   |
   +--> Validate
   |
   +--> Commit
           |
           v
   Destination Business Models
```

The generic import layer owns the lifecycle. Domain handlers own domain-specific validation and persistence.

---

## 4. Data Model

### ImportBatch

Represents one uploaded spreadsheet.

| Field              | Purpose                           |
| ------------------ | --------------------------------- |
| `id`               | UUID identifying the batch        |
| `import_type`      | Type of import                    |
| `file_name`        | Original filename                 |
| `file_path`        | Path/key in Django storage        |
| `org_node`         | Optional organization context     |
| `reporting_period` | Optional reporting-period context |
| `module_code`      | Optional module context           |
| `status`           | Current lifecycle status          |
| `total_rows`       | Number of parsed rows             |
| `valid_rows`       | Number of valid rows              |
| `error_rows`       | Number of error rows              |
| `uploaded_by`      | Uploading user                    |
| `uploaded_at`      | Upload timestamp                  |
| `committed_at`     | Commit timestamp                  |

### ImportRow

Represents one parsed spreadsheet row.

| Field        | Purpose                      |
| ------------ | ---------------------------- |
| `batch`      | Parent import batch          |
| `row_number` | Original Excel row number    |
| `raw_data`   | JSON-safe row data           |
| `status`     | Row processing status        |
| `errors`     | Structured validation errors |

Row statuses:

```text
VALID
ERROR
SKIPPED
COMMITTED
```

Committed batches are immutable and cannot be directly modified or deleted.

---

## 5. Upload Context

The upload API accepts:

```text
file
import_type
module_code       optional
org_node          optional
reporting_period  optional
```

`module_code` is validated against the Module Registry.

`org_node` is resolved against `OrgNode`, and `reporting_period` is resolved against `ReportingPeriod`. Invalid referenced IDs are rejected.

The context is persisted on `ImportBatch` and exposed by the batch serializer.

---

## 6. ExcelParser

`ExcelParser` provides generic spreadsheet-level processing.

It:

* Supports `.xlsx` files only
* Accepts filesystem paths and file-like objects
* Enforces a 10 MB maximum file size
* Uses `openpyxl` read-only mode
* Validates headers
* Rejects empty or duplicate headers
* Skips blank rows
* Preserves Excel row numbers
* Converts common values such as dates and decimals to JSON-safe values

The parser contains no domain-specific import logic.

---

## 7. ImportUploadService

The upload service:

1. Validates the optional module context.
2. Saves the uploaded file through Django's configured storage backend.
3. Opens the stored file through Django storage.
4. Parses the XLSX file.
5. Creates the `ImportBatch`.
6. Creates `ImportRow` records in database chunks.
7. Sets the batch status to `UPLOADED`.
8. Records the upload activity.

Upload does not validate destination business data and does not create destination business records.

If processing fails after storage, the uploaded file is cleaned up.

---

## 8. ImportHandler

Domain-specific behavior is provided through:

```python
class ImportHandler:
    def validate_row(self, raw_data):
        ...

    def validate_batch(self, rows):
        ...

    def commit(self, batch):
        ...
```

* `validate_row()` validates and normalizes one row.
* `validate_batch()` can perform cross-row or batch-level checks.
* `commit()` writes validated data to destination models.

---

## 9. ImportHandlerRegistry

`ImportHandlerRegistry` maps an `import_type` to its handler.

If no handler is registered, validation and commit fail explicitly:

```json
{
  "import_type": [
    "No import handler is registered for ANSWERS."
  ]
}
```

This prevents unsupported imports from being marked as successful.

---

## 10. Batch Lifecycle

```text
UPLOADED
    |
    v
VALIDATING
    |
    +----> FAILED
    |         |
    |         v
    |     VALIDATING
    |
    v
VALIDATED
    |
    v
COMMITTED
```

Available batch statuses:

```text
UPLOADED
VALIDATING
VALIDATED
FAILED
COMMITTED
```

A failed batch can be validated again.

---

## 11. Validation

`ImportBatchService.validate_batch()`:

1. Checks that the batch is eligible for validation.
2. Gets the registered handler.
3. Sets the batch to `VALIDATING`.
4. Validates each row through `validate_row()`.
5. Stores normalized data and row errors.
6. Runs optional batch-level validation.
7. Updates `valid_rows` and `error_rows`.
8. Sets the final status to `VALIDATED` when there are no errors, otherwise `FAILED`.
9. Records a batch-level ActivityLog event.

Validation does not write destination business data.

---

## 12. Commit

Only a batch in `VALIDATED` status can be committed.

Commit:

1. Locks and re-reads the batch with `select_for_update()`.
2. Re-checks its current status.
3. Gets the registered handler.
4. Executes `handler.commit(batch)`.
5. Marks the batch `COMMITTED`.
6. Sets `committed_at`.
7. Marks valid rows as `COMMITTED`.
8. Records the commit activity.

Commit runs inside `transaction.atomic()`.

If the handler raises an exception, destination writes and commit state are rolled back.

Concurrent commit requests are protected by database row locking.

---

## 13. API

### Upload

```http
POST /api/imports/batches/
```

Multipart fields:

```text
file
import_type
module_code       optional
org_node          optional
reporting_period  optional
```

### Batch Detail

```http
GET /api/imports/batches/<batch_id>/
```

### Row Preview

```http
GET /api/imports/batches/<batch_id>/rows/
```

Query parameters:

```text
?page=2
?page_size=50
?status=ERROR
```

Default page size is `20`; maximum is `100`.

Supported row filters:

```text
VALID
ERROR
SKIPPED
COMMITTED
```

### Validate

```http
POST /api/imports/batches/<batch_id>/validate/
```

### Commit

```http
POST /api/imports/batches/<batch_id>/commit/
```

---

## 14. API Security

Import APIs require authentication.

Normal users can access only batches they uploaded. Superusers can access batches across users.

The ownership check applies to batch detail, row preview, validation, and commit operations.

---

## 15. Activity Logging

Import lifecycle events use the existing `ActivityLog`.

The implementation records batch-level events such as:

```text
IMPORT_BATCH_UPLOADED
IMPORT_BATCH_VALIDATED
IMPORT_BATCH_VALIDATION_FAILED
IMPORT_BATCH_COMMITTED
```

Activity logging is not performed once per spreadsheet row.

---

## 16. Error Handling

The infrastructure handles:

* Missing or unsupported files
* Malformed XLSX files
* Invalid, empty, or duplicate headers
* Files larger than 10 MB
* Invalid module codes
* Invalid organization-node IDs
* Invalid reporting-period IDs
* Row validation errors
* Missing import handlers
* Invalid lifecycle transitions
* Commit failures

Validation errors are stored on `ImportRow.errors`.

A failed commit does not mark the batch as `COMMITTED`.

---

## 17. Testing Coverage

The implementation includes tests for:

* XLSX parsing
* File-size protection
* File-like uploads
* Blank rows and row numbers
* JSON-safe cell values
* Batch and row creation
* Upload context validation
* Module validation
* Organization-node and reporting-period context
* Validation success and failure
* Revalidation
* Unsupported handlers
* Commit protection
* Transaction rollback
* Concurrent commit protection
* Committed-batch immutability
* Authentication and ownership
* Row pagination and status filtering
* ActivityLog behavior

Test-only handlers are registered within tests rather than production startup.

---

## 18. Future Import Handlers

Future modules only need to implement their domain-specific handler and register it for the required import type.

For example:

```python
class DatapointsImportHandler(ImportHandler):
    def validate_row(self, raw_data):
        ...

    def validate_batch(self, rows):
        ...

    def commit(self, batch):
        ...
```

The existing upload, parsing, preview, validation, lifecycle, and commit infrastructure can then be reused.

---

## 19. Current M13 Scope

Implemented:

* `ImportBatch`
* `ImportRow`
* `ExcelParser`
* `ImportUploadService`
* `ImportBatchService`
* `ImportHandler`
* `ImportHandlerRegistry`
* Django storage integration
* 10 MB upload limit
* Upload context
* Module validation
* Organization and reporting-period context
* Validation and revalidation
* Row-level errors
* Row preview pagination/filtering
* Transactional commit
* Concurrent commit protection
* Committed-batch immutability
* Authentication and ownership checks
* ActivityLog integration
* Test-only fake handler

Not included in the generic foundation:

* Production Datapoints importer
* Production Framework Nodes importer
* Production Stakeholders importer
* Production Emission Factors importer

The production `ANSWERS` handler is documented below as the M13/M5 integration.

---

## 20. Summary

M13 provides one reusable import pipeline:

```text
UPLOAD
  |
  v
UPLOADED
  |
  v
VALIDATING
  |
  +----> FAILED ----> VALIDATING
  |
  v
VALIDATED
  |
  v
COMMITTED
```

The foundation manages generic import infrastructure, while domain handlers manage domain validation and destination business-data persistence.

---

# 21. ANSWERS Import (M5)

The production `ANSWERS` handler imports scalar M5 Answer values into existing DataRequest/Submissions.

The importer does not create DataRequests or Submissions.

The existing M5 `DataRequest`, `Submission`, and `Answer` models/services remain authoritative.

For this production slice, imported data is limited to editable DRAFT capture data. The importer never auto-submits, auto-approves, or auto-rejects an M5 submission.

---

## 21.1 Workbook schema

The canonical ANSWERS workbook uses these headers:

| Header           | Required                                        | Meaning                                                  |
| ---------------- | ----------------------------------------------- | -------------------------------------------------------- |
| `datapoint_code` | Yes                                             | Canonical M4 Datapoint code                              |
| `value`          | According to datapoint type and draft semantics | Value to be stored according to the datapoint type       |
| `unit_code`      | Conditional                                     | Canonical Unit code for datapoints with a UnitFamily     |
| `org_node_code`  | Conditional                                     | Target OrgNode when the ImportBatch has no fixed OrgNode |
| `entry_note`     | No                                              | Optional source/entry note                               |

The first production ANSWERS importer supports these scalar datapoint types:

```text
DECIMAL
INTEGER
TEXT
LONG_TEXT
BOOLEAN
SELECT
DATE
```

The importer accepts only canonical M4 datapoints.

`TABLE` datapoints are not currently supported by the ANSWERS importer. TABLE import is reserved for a future extension of the handler.

The final workbook template must use the exact headers listed above.

## 21.1.1 Example XLSX Workbook

The production ANSWERS importer expects an `.xlsx` workbook containing a single worksheet for the scalar import contract.

The worksheet must contain the exact canonical headers:

| datapoint_code     | value      | unit_code | org_node_code | entry_note                      |
| ------------------ | ---------- | --------- | ------------- | ------------------------------- |
| ENERGY_CONSUMPTION | 1250.50    | MWH       | PLANT_001     | Monthly electricity consumption |
| EMPLOYEE_COUNT     | 250        |           | PLANT_001     | Total employees                 |
| RENEWABLE_ENERGY   | TRUE       |           | PLANT_001     | Renewable energy usage          |
| REPORTING_STATUS   | Complete   |           | PLANT_001     | Reporting status                |
| REPORTING_DATE     | 2026-08-14 |           | PLANT_001     | Reporting date                  |
| WATER_CONSUMPTION  | 450.75     | M3        | PLANT_001     | Water consumption               |

### Required columns

`datapoint_code` is always required.

`value` is required according to the target datapoint's type and draft-value rules.

### Conditional columns

`unit_code` is required when the canonical M4 Datapoint declares a `UnitFamily`.

`org_node_code` is required when the `ImportBatch` does not have a fixed `org_node`.

If the batch has a fixed `org_node`, the `org_node_code` column may be left blank. If it is supplied, it must resolve to the same OrgNode as the batch.

`entry_note` is optional.

### Value examples

The `value` column must contain values compatible with the canonical M4 Datapoint type.

| Datapoint type | Example value                      |
| -------------- | ---------------------------------- |
| `DECIMAL`      | `1250.50`                          |
| `INTEGER`      | `250`                              |
| `TEXT`         | `Complete`                         |
| `LONG_TEXT`    | `Monthly sustainability narrative` |
| `BOOLEAN`      | `TRUE`                             |
| `SELECT`       | `Complete`                         |
| `DATE`         | `2026-08-14`                       |

Boolean and date values must use representations accepted by the production importer. Invalid or ambiguous values are rejected during validation.

SELECT values must correspond to an active option registered for the target M4 Datapoint.

### Example workbook rules

The uploaded workbook must satisfy the following rules:

1. The file must be an `.xlsx` workbook.
2. The workbook must use the exact canonical ANSWERS headers.
3. Headers must not be duplicated.
4. `datapoint_code` must resolve to an active canonical M4 Datapoint.
5. Only scalar datapoint types are supported.
6. `TABLE` datapoints must not be included.
7. `unit_code` must be supplied when required by the datapoint's UnitFamily.
8. `org_node_code` must resolve to the target OrgNode when the batch has no fixed OrgNode.
9. Each `datapoint_code + org_node_code + reporting_period` target must occur only once in the workbook.
10. Blank spreadsheet rows are ignored by the generic XLSX parser.
11. The workbook's reporting period is supplied by the ImportBatch and is not selected independently by individual rows.
12. The workbook does not create DataRequests or Submissions.

### Recommended workbook structure

For a normal production upload, the workbook should look conceptually like:

```text
answers.xlsx
└── Answers
    ├── datapoint_code
    ├── value
    ├── unit_code
    ├── org_node_code
    └── entry_note
```

The importer treats the workbook as input data only. It does not use spreadsheet formatting, formulas, comments, or additional business-specific columns as part of the production ANSWERS contract.

The canonical workbook template should therefore contain only the supported ANSWERS columns and data required by the import contract.

### Example upload context

The workbook is uploaded together with the ImportBatch context:

```text
file              = answers.xlsx
import_type       = ANSWERS
module_code       = energy
org_node          = <optional-org-node-id>
reporting_period  = <reporting-period-id>
```

The `reporting_period`, optional fixed `org_node`, and optional `module_code` are ImportBatch context rather than spreadsheet columns.


---

## 21.2 Batch and row context

The ImportBatch provides shared context:

* `reporting_period`
* optional `org_node`
* optional `module_code`
* `uploaded_by`

Each row provides the datapoint/value information and, when required, the target `org_node_code`.

The ReportingPeriod supplied on the ImportBatch is the authoritative reporting period for the workbook. Rows do not independently select arbitrary reporting periods.

When the batch has a fixed OrgNode, a row may omit `org_node_code`. If it is provided, it must match the batch OrgNode.

When the batch has no fixed OrgNode, every row must provide an `org_node_code` resolving to exactly one active OrgNode.

The batch `module_code`, when supplied, must match the canonical M4 Datapoint's Module Registry module.

---

## 21.3 Datapoint and unit resolution

`datapoint_code` resolves only to an active canonical M4 Datapoint.

The importer rejects:

* missing datapoints
* inactive datapoints
* unsupported datapoint types
* `TABLE` datapoints
* datapoints belonging to a different batch module

Units are resolved through the canonical M4 Unit/UnitFamily relationship.

If the datapoint declares a UnitFamily:

* `unit_code` is required
* the Unit must exist
* the Unit must be active
* the Unit must belong to the datapoint's UnitFamily

If the datapoint does not accept a Unit, supplying `unit_code` is rejected.

---

## 21.4 DataRequest resolution

For every valid target row, the importer resolves the existing M5 DataRequest using:

```text
Datapoint + OrgNode + ReportingPeriod
```

The importer never creates a DataRequest.

The matching DataRequest must:

* exist
* be `OPEN`
* have a current Submission
* have a `DRAFT` Submission

The Submission is the destination for the imported Answer.

If no eligible DataRequest exists, the row fails validation with a structured error.

The importer does not overwrite:

* request assignee
* due date
* instructions
* campaign linkage
* request lifecycle

---

## 21.5 Validation

Row validation is read-only with respect to M5 destination records.

Validation performs:

1. Canonical datapoint resolution.
2. Supported scalar type validation.
3. Module consistency validation.
4. ReportingPeriod validation.
5. OrgNode resolution.
6. Collection-level validation.
7. Authorization validation.
8. Existing DataRequest resolution.
9. DataRequest lifecycle validation.
10. Submission lifecycle validation.
11. Unit validation.
12. Value normalization.
13. SELECT option validation.
14. M5 typed-value validation.
15. Duplicate datapoint + OrgNode + ReportingPeriod detection across workbook rows.

Normalized values are stored on the ImportRow only after successful validation.

No Answer is written during preview or validation.

Existing M5 submit-time validation remains authoritative for required evidence and completeness. Evidence is not required merely to save an otherwise valid draft through the import.

---

## 21.6 Value normalization

Values are normalized according to the canonical M4 Datapoint definition and existing M5 typed-value rules.

The implementation must apply deterministic parsing for BOOLEAN and DATE values.

BOOLEAN parsing accepts only the representations explicitly supported by the implementation. Invalid or ambiguous boolean values are rejected.

DATE values are normalized to the canonical date representation used by M5. Invalid date values are rejected.

DECIMAL and INTEGER values are validated using the canonical datapoint validation metadata and are stored using the existing M5 typed-value semantics.

SELECT values must resolve to a registered active option for the target datapoint.

The importer does not introduce a second type-validation system.

---

## 21.7 Authorization

ANSWERS import authorization follows the M5 maker/manager contract.

A superuser may import.

An authorized manager may import when `data.manage` covers the target OrgNode.

A maker may import only when:

1. the maker is the assigned user on the target DataRequest; and
2. the maker has `data.enter` permission covering the target OrgNode.

Having `data.enter` for the OrgNode is not sufficient by itself for an unassigned maker.

Permission and OrgNode scope must come from the same qualifying assignment.

Unrelated role and scope assignments must not be combined to manufacture authorization.

Cross-scope UUID/code knowledge must not allow imported writes outside the uploader's authorized scope.

Authorization is checked during validation and rechecked during commit where mutable authorization state may have changed after preview.

---

## 21.8 DRAFT-only behavior

ANSWERS imports may populate only a current `DRAFT` Submission belonging to an `OPEN` DataRequest.

Submitted, approved, or otherwise non-editable submissions cannot be populated by the importer.

The ReportingPeriod must also remain active and writable according to the M3/M5 lifecycle rules.

These lifecycle conditions are checked during validation and revalidated during commit because they may change between preview and commit.

The importer never:

* submits a Submission
* approves a Submission
* rejects a Submission
* bypasses reviewer workflow

The resulting draft continues through the normal M5 maker and review workflow.

---

## 21.9 Commit and revalidation

Only a successfully validated ImportBatch may be committed.

During commit, the handler re-resolves mutable domain state, including:

* active canonical Datapoint
* active OrgNode
* active/open ReportingPeriod
* existing DataRequest
* DataRequest authorization
* current Submission
* `DRAFT` Submission status
* active Unit
* UnitFamily compatibility
* active SELECT option

Destination Answer writes occur only during commit.

The generic M13 commit service runs inside a transaction.

If any row fails during commit:

* all M5 destination writes are rolled back;
* the ImportBatch is not marked `COMMITTED`;
* the batch remains available for error inspection/revalidation according to the generic M13 lifecycle.

Commit does not create or modify request/campaign metadata.

---

## 21.10 Update and idempotency

The same ImportBatch cannot commit twice. The generic M13 one-way lifecycle remains authoritative.

A separate later workbook containing a row for an already-existing editable draft must not create a duplicate Answer.

The target request is resolved using the canonical:

```text
Datapoint + OrgNode + ReportingPeriod
```

relationship.

Workbook rows are also checked for duplicate:

```text
datapoint_code + org_node_code + reporting_period
```

combinations.

Duplicate target rows within the same workbook are rejected clearly rather than silently applying multiple values.

If an existing editable draft Answer already exists, the importer updates it only through the supported M5 draft-save semantics.

A later import must never rewrite submitted or approved historical data.

---

## 21.11 Provenance

The resulting Answer is written through the canonical M5 data-capture service with the importing user as the actor.

The import result remains traceable to the originating import without storing the entire spreadsheet row as opaque data on the Answer.

The provenance contract retains the import context needed to answer:

```text
Which workbook/batch/row created or last populated this imported draft Answer?
```

The import provenance includes, as applicable:

* importing/uploading user
* source workbook filename
* ImportBatch
* ImportRow
* original Excel row number
* batch timestamp
* normalized import row data
* validation errors
* resulting Answer association

If the M13-to-M5 integration uses an explicit nullable result reference from `ImportRow` to `Answer`, that relationship is the durable row-level provenance link.

The provenance relationship must not duplicate the canonical Answer data or introduce a parallel Answer model.

M13 ActivityLog records batch-level upload, validation, validation failure, and commit events.

---

## 21.12 API/runtime example

The normal M13 flow is:

```text
POST /api/imports/batches/
        |
        v
     UPLOADED
        |
        v
POST /api/imports/batches/{id}/validate/
        |
        v
 preview rows/errors
        |
        v
POST /api/imports/batches/{id}/commit/
        |
        v
    COMMITTED
        |
        v
M5 DataRequest -> DRAFT Submission -> Answer
```

Import APIs require authenticated Django sessions and the normal CSRF protection for unsafe requests.

Example upload:

```text
POST /api/imports/batches/

file=@answers.xlsx
import_type=ANSWERS
module_code=energy
org_node=<optional-org-node-id>
reporting_period=<reporting-period-id>
```

After successful commit, the resulting Answer is available through the normal M5 Data Capture API rather than through an import-specific answer store.

The imported draft remains subject to the normal M5 submit/review/approval workflow.

---

## 21.13 TABLE limitation and future extension

The first production ANSWERS importer supports scalar datapoints only:

```text
DECIMAL
INTEGER
TEXT
LONG_TEXT
BOOLEAN
SELECT
DATE
```

`TABLE` datapoints are deliberately rejected in this release.

TABLE import is deferred because it requires a separate workbook representation for:

* canonical TABLE rows
* dynamic rows
* table columns
* typed table cells
* fixed-row identity
* display order
* column-specific validation
* required cells
* minimum row requirements

The future implementation must write through the existing M5 `AnswerTableRow` and `AnswerTableCell` domain rather than introducing a parallel import-specific table model.

The future TABLE contract should be implemented as a follow-up change after the row/cell spreadsheet representation and validation rules are explicitly defined.

---

# 22. Integration Boundaries

The M13/M5 ANSWERS integration follows these ownership boundaries:

| Concern                            | Authoritative owner                          |
| ---------------------------------- | -------------------------------------------- |
| XLSX upload                        | M13                                          |
| Spreadsheet parsing                | M13                                          |
| ImportBatch lifecycle              | M13                                          |
| ImportRow lifecycle                | M13                                          |
| Generic preview                    | M13                                          |
| Canonical Datapoint definition     | M4                                           |
| Canonical Unit/UnitFamily          | M4                                           |
| OrgNode hierarchy                  | M2                                           |
| ReportingPeriod lifecycle          | M3/M5                                        |
| DataRequest                        | M5                                           |
| Submission                         | M5                                           |
| Answer                             | M5                                           |
| M5 typed-value semantics           | M5                                           |
| M5 authorization/scoping           | M5/RBAC                                      |
| Domain-specific ANSWERS validation | M13 Answers handler using M4/M5 contracts    |
| ANSWERS destination writes         | M13 Answers handler through accepted M5 path |

The integration does not create a second answer, request, submission, period, organization scope, permission system, or validation system.

---

# 23. Production ANSWERS Scope

The production ANSWERS handler is limited to canonical scalar datapoints and existing M5 capture requests.

Included:

* `DECIMAL`
* `INTEGER`
* `TEXT`
* `LONG_TEXT`
* `BOOLEAN`
* `SELECT`
* `DATE`
* Canonical M4 datapoint resolution
* Canonical unit resolution
* OrgNode resolution
* ReportingPeriod context
* Existing DataRequest resolution
* Existing current DRAFT Submission resolution
* Scoped authorization
* Row-level validation errors
* Duplicate target detection
* Typed Answer creation/update
* DRAFT-only behavior
* Transaction-safe commit
* Revalidation at commit
* Import provenance

Not included:

* TABLE row/cell Excel import
* Automatic DataRequest creation
* Automatic campaign creation
* Automatic submission
* Automatic approval
* Automatic rejection
* Evidence-file import from workbook paths
* Frontend upload wizard
* BRSR/GRI-specific answer storage
* Framework-node imports
* Datapoint-definition imports
* Stakeholder imports
* Emission-factor imports
* M6 calculations
* M8 reporting changes
* Notification producer integrations
* RBAC redesign

---

# 24. Verification

The ANSWERS import implementation is covered by automated tests for the
production scalar import contract, including:

- scalar datapoint types;
- datapoint and unit resolution;
- value and type validation;
- SELECT option validation;
- OrgNode and ReportingPeriod validation;
- module and collection-level compatibility;
- DataRequest and Submission lifecycle validation;
- authorization and same-assignment scope enforcement;
- duplicate-row handling;
- validation without M5 destination writes;
- DRAFT Answer creation and update;
- transaction rollback;
- import idempotency;
- provenance;
- protection against cross-scope writes;
- rejection of unsupported TABLE datapoints.

The implementation also uses the existing M13 upload, validation, preview,
and commit APIs.

For runtime acceptance, the real application should be exercised with a
canonical `.xlsx` workbook using authenticated session and CSRF-protected
requests. The runtime flow should confirm that a successfully committed
import produces an M5 DRAFT Answer that remains available through the normal
M5 workflow.

TABLE import and frontend upload UI remain follow-up work.
