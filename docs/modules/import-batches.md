# M13 --- Import Batch Foundation

## 1. Purpose

The M13 Import Batch Foundation provides reusable infrastructure for
spreadsheet-based imports in ESG_360.

It handles:

-   Excel upload and Django storage
-   XLSX parsing
-   Import batch and row creation
-   Row-level validation
-   Error tracking
-   Revalidation
-   Preview pagination and filtering
-   Transaction-safe commit
-   Import lifecycle tracking
-   Activity logging

Domain-specific validation and destination writes are handled by
`ImportHandler` implementations.

## 2. Supported Import Types

``` text
ANSWERS
DATAPOINTS
FRAMEWORK_NODES
STAKEHOLDERS
EMISSION_FACTORS
```

These values define supported import categories. A handler must be
registered before an import can be validated or committed.

`FakeAnswersImportHandler` is test-only and is not registered during
production startup.

## 3. Architecture

``` text
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

The generic import layer owns the lifecycle. Domain handlers own
domain-specific validation and persistence.

## 4. Data Model

### ImportBatch

Represents one uploaded spreadsheet.

  Field                Purpose
  -------------------- -----------------------------------
  `id`                 UUID identifying the batch
  `import_type`        Type of import
  `file_name`          Original filename
  `file_path`          Path/key in Django storage
  `org_node`           Optional organization context
  `reporting_period`   Optional reporting-period context
  `module_code`        Optional module context
  `status`             Current lifecycle status
  `total_rows`         Number of parsed rows
  `valid_rows`         Number of valid rows
  `error_rows`         Number of error rows
  `uploaded_by`        Uploading user
  `uploaded_at`        Upload timestamp
  `committed_at`       Commit timestamp

### ImportRow

Represents one parsed spreadsheet row.

  Field          Purpose
  -------------- ------------------------------
  `batch`        Parent import batch
  `row_number`   Original Excel row number
  `raw_data`     JSON-safe row data
  `status`       Row processing status
  `errors`       Structured validation errors

Row statuses:

``` text
VALID
ERROR
SKIPPED
COMMITTED
```

Committed batches are immutable and cannot be directly modified or
deleted.

## 5. Upload Context

The upload API accepts:

``` text
file
import_type
module_code       optional
org_node          optional
reporting_period  optional
```

`module_code` is validated against the Module Registry.

`org_node` is resolved against `OrgNode`, and `reporting_period` is
resolved against `ReportingPeriod`. Invalid referenced IDs are rejected.

The context is persisted on `ImportBatch` and exposed by the batch
serializer.

## 6. ExcelParser

`ExcelParser` provides generic spreadsheet-level processing.

It:

-   Supports `.xlsx` files only
-   Accepts filesystem paths and file-like objects
-   Enforces a 10 MB maximum file size
-   Uses `openpyxl` read-only mode
-   Validates headers
-   Rejects empty or duplicate headers
-   Skips blank rows
-   Preserves Excel row numbers
-   Converts common values such as dates and decimals to JSON-safe
    values

The parser contains no domain-specific import logic.

## 7. ImportUploadService

The upload service:

1.  Validates the optional module context.
2.  Saves the uploaded file through Django's configured storage backend.
3.  Opens the stored file through Django storage.
4.  Parses the XLSX file.
5.  Creates the `ImportBatch`.
6.  Creates `ImportRow` records in database chunks.
7.  Sets the batch status to `UPLOADED`.
8.  Records the upload activity.

Upload does not validate destination business data and does not create
destination business records.

If processing fails after storage, the uploaded file is cleaned up.

## 8. ImportHandler

Domain-specific behavior is provided through:

``` python
class ImportHandler:
    def validate_row(self, raw_data):
        ...

    def validate_batch(self, rows):
        ...

    def commit(self, batch):
        ...
```

-   `validate_row()` validates and normalizes one row.
-   `validate_batch()` can perform cross-row or batch-level checks.
-   `commit()` writes validated data to destination models.

## 9. ImportHandlerRegistry

`ImportHandlerRegistry` maps an `import_type` to its handler.

If no handler is registered, validation and commit fail explicitly:

``` json
{
  "import_type": [
    "No import handler is registered for ANSWERS."
  ]
}
```

This prevents unsupported imports from being marked as successful.

## 10. Batch Lifecycle

``` text
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

``` text
UPLOADED
VALIDATING
VALIDATED
FAILED
COMMITTED
```

A failed batch can be validated again.

## 11. Validation

`ImportBatchService.validate_batch()`:

1.  Checks that the batch is eligible for validation.
2.  Gets the registered handler.
3.  Sets the batch to `VALIDATING`.
4.  Validates each row through `validate_row()`.
5.  Stores normalized data and row errors.
6.  Runs optional batch-level validation.
7.  Updates `valid_rows` and `error_rows`.
8.  Sets the final status to `VALIDATED` when there are no errors,
    otherwise `FAILED`.
9.  Records a batch-level ActivityLog event.

Validation does not write destination business data.

## 12. Commit

Only a batch in `VALIDATED` status can be committed.

Commit:

1.  Locks and re-reads the batch with `select_for_update()`.
2.  Re-checks its current status.
3.  Gets the registered handler.
4.  Executes `handler.commit(batch)`.
5.  Marks the batch `COMMITTED`.
6.  Sets `committed_at`.
7.  Marks valid rows as `COMMITTED`.
8.  Records the commit activity.

Commit runs inside `transaction.atomic()`.

If the handler raises an exception, destination writes and commit state
are rolled back.

Concurrent commit requests are protected by database row locking.

## 13. API

### Upload

``` http
POST /api/imports/batches/
```

Multipart fields:

``` text
file
import_type
module_code       optional
org_node          optional
reporting_period  optional
```

### Batch Detail

``` http
GET /api/imports/batches/<batch_id>/
```

### Row Preview

``` http
GET /api/imports/batches/<batch_id>/rows/
```

Query parameters:

``` text
?page=2
?page_size=50
?status=ERROR
```

Default page size is `20`; maximum is `100`.

Supported row filters:

``` text
VALID
ERROR
SKIPPED
COMMITTED
```

### Validate

``` http
POST /api/imports/batches/<batch_id>/validate/
```

### Commit

``` http
POST /api/imports/batches/<batch_id>/commit/
```

## 14. API Security

Import APIs require authentication.

Normal users can access only batches they uploaded. Superusers can
access batches across users.

The ownership check applies to batch detail, row preview, validation,
and commit operations.

## 15. Activity Logging

Import lifecycle events use the existing `ActivityLog`.

The implementation records batch-level events such as:

``` text
IMPORT_BATCH_UPLOADED
IMPORT_BATCH_VALIDATED
IMPORT_BATCH_VALIDATION_FAILED
IMPORT_BATCH_COMMITTED
```

Activity logging is not performed once per spreadsheet row.

## 16. Error Handling

The infrastructure handles:

-   Missing or unsupported files
-   Malformed XLSX files
-   Invalid, empty, or duplicate headers
-   Files larger than 10 MB
-   Invalid module codes
-   Invalid organization-node IDs
-   Invalid reporting-period IDs
-   Row validation errors
-   Missing import handlers
-   Invalid lifecycle transitions
-   Commit failures

Validation errors are stored on `ImportRow.errors`.

A failed commit does not mark the batch as `COMMITTED`.

## 17. Testing Coverage

The implementation includes tests for:

-   XLSX parsing
-   File-size protection
-   File-like uploads
-   Blank rows and row numbers
-   JSON-safe cell values
-   Batch and row creation
-   Upload context validation
-   Module validation
-   Organization-node and reporting-period context
-   Validation success and failure
-   Revalidation
-   Unsupported handlers
-   Commit protection
-   Transaction rollback
-   Concurrent commit protection
-   Committed-batch immutability
-   Authentication and ownership
-   Row pagination and status filtering
-   ActivityLog behavior

Test-only handlers are registered within tests rather than production
startup.

## 18. Future Import Handlers

Future modules only need to implement their domain-specific handler and
register it for the required import type.

For example:

``` python
class DatapointsImportHandler(ImportHandler):
    def validate_row(self, raw_data):
        ...

    def validate_batch(self, rows):
        ...

    def commit(self, batch):
        ...
```

The existing upload, parsing, preview, validation, lifecycle, and commit
infrastructure can then be reused.

## 19. Current M13 Scope

Implemented:

-   `ImportBatch`
-   `ImportRow`
-   `ExcelParser`
-   `ImportUploadService`
-   `ImportBatchService`
-   `ImportHandler`
-   `ImportHandlerRegistry`
-   Django storage integration
-   10 MB upload limit
-   Upload context
-   Module validation
-   Organization and reporting-period context
-   Validation and revalidation
-   Row-level errors
-   Row preview pagination/filtering
-   Transactional commit
-   Concurrent commit protection
-   Committed-batch immutability
-   Authentication and ownership checks
-   ActivityLog integration
-   Test-only fake handler

Not included:

-   Production Answers importer
-   Production Datapoints importer
-   Production Framework Nodes importer
-   Production Stakeholders importer
-   Production Emission Factors importer

These require their respective domain-specific handlers.

## 20. Summary

M13 provides one reusable import pipeline:

``` text
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

The foundation manages generic import infrastructure, while future
domain handlers manage domain validation and destination business-data
persistence.
