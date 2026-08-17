# Import Batches

## Purpose

The Import Batches infrastructure provides a shared, reusable pipeline for importing spreadsheet-based data into ESG_360.

Instead of implementing separate upload, parsing, validation, error tracking, re-validation, and commit logic inside every feature, ESG_360 provides a common import-batch foundation.

The same infrastructure can later be reused by different domains such as:

* Answers
* Datapoints
* Framework Nodes
* Stakeholders
* Emission Factors
* Other future bulk-import features

The import infrastructure separates the **spreadsheet-processing lifecycle** from the **destination business logic**.

The generic infrastructure is responsible for:

1. Receiving and storing the uploaded spreadsheet.
2. Creating an `ImportBatch`.
3. Parsing spreadsheet rows.
4. Creating `ImportRow` records.
5. Locating the appropriate domain import handler.
6. Validating rows through the registered handler.
7. Storing row-level validation errors.
8. Tracking validation counts and batch status.
9. Allowing failed batches to be validated again.
10. Committing a validated batch through the appropriate domain handler.
11. Tracking the import lifecycle.
12. Recording meaningful lifecycle activity through the existing `ActivityLog` infrastructure.

The infrastructure does **not** contain feature-specific business-table creation logic.

The key architectural rule is:

> Parsing and validation operate on `ImportBatch` and `ImportRow`; destination business tables are modified only during an explicit commit performed through the appropriate domain import handler.

---

# Architecture

The import system is divided into four main responsibilities:

```text
Uploaded Spreadsheet
        |
        v
ImportUploadService
        |
        | creates/stores
        v
ImportBatch
        |
        v
ImportBatchService
        |
        +----------------------+
        |                      |
        v                      v
   ExcelParser        ImportHandlerRegistry
        |                      |
        |                      v
        |              Domain Import Handler
        |                      |
        +----------+-----------+
                   |
                   v
              ImportRow
                   |
                   v
        Destination Business Model
```

The responsibilities are intentionally separated.

### `ImportUploadService`

Handles the initial upload operation.

Its responsibilities include:

* Receiving the uploaded Excel file.
* Validating the import request.
* Validating the supplied module information against the Module Registry when applicable.
* Storing the uploaded file.
* Creating the `ImportBatch`.

It does not implement domain-specific validation or destination-table creation.

### `ExcelParser`

Handles spreadsheet-level parsing.

It is responsible for:

* Opening the Excel workbook.
* Reading spreadsheet rows.
* Extracting headers and row values.
* Skipping blank rows according to the parser rules.
* Converting spreadsheet values into JSON-safe data where required.
* Returning structured row information to the import infrastructure.

It does not know how an Answer, Datapoint, Framework Node, Stakeholder, or Emission Factor should be interpreted or persisted.

### `ImportBatchService`

Coordinates the import lifecycle.

It is responsible for:

* Retrieving the appropriate handler.
* Parsing and processing rows.
* Creating/updating `ImportRow` processing state.
* Running handler validation.
* Calculating valid/error row counts.
* Updating batch status.
* Re-validating failed batches.
* Protecting the commit transition.
* Invoking the registered handler during commit.
* Updating the final batch and row states.

### `ImportHandlerRegistry`

Provides the connection between an `import_type` and the domain-specific handler responsible for that import.

This prevents `ImportBatchService` from containing feature-specific conditional logic such as:

```python
if import_type == "ANSWERS":
    ...
elif import_type == "DATAPOINTS":
    ...
elif import_type == "FRAMEWORK_NODES":
    ...
```

Instead, the registry selects the appropriate handler.

---

# Data Model

## ImportBatch

`ImportBatch` represents one uploaded spreadsheet and its complete processing lifecycle.

The model contains information such as:

| Field              | Description                                           |
| ------------------ | ----------------------------------------------------- |
| `id`               | UUID primary key identifying the import batch         |
| `import_type`      | Identifies what type of data the spreadsheet contains |
| `file_name`        | Original uploaded filename                            |
| `file_path`        | Stored file location                                  |
| `org_node`         | Optional organization scope                           |
| `reporting_period` | Optional reporting-period context                     |
| `module_code`      | Optional module identifier associated with the import |
| `status`           | Current lifecycle state of the batch                  |
| `total_rows`       | Total number of parsed spreadsheet rows               |
| `valid_rows`       | Number of rows that passed validation                 |
| `error_rows`       | Number of rows containing validation errors           |
| `uploaded_by`      | User who uploaded the spreadsheet                     |
| `uploaded_at`      | Time at which the batch was uploaded/created          |
| `committed_at`     | Time at which the batch was successfully committed    |

### Import types

The current import type choices include:

* `ANSWERS`
* `DATAPOINTS`
* `FRAMEWORK_NODES`
* `STAKEHOLDERS`
* `EMISSION_FACTORS`

These values identify the type of import and are used to locate the corresponding handler.

A listed import type does not automatically mean that its production destination handler has already been implemented.

The M13 foundation provides the infrastructure and handler contract.

---

## ImportBatch Relationships

`uploaded_by` references the application's user model.

`module_code`, when supplied, is validated against the controlled Module Registry rather than being treated as an arbitrary feature code.

`org_node` and `reporting_period` provide optional context for imports that require organization or reporting-period scope.

The relationship can be represented as:

```text
ImportBatch
    |
    +-- uploaded_by
    |
    +-- module_code
    |       |
    |       v
    |   Module Registry
    |
    +-- org_node
    |
    +-- reporting_period
    |
    +-- ImportRow
```

---

# ImportRow

`ImportRow` represents an individual parsed spreadsheet row belonging to an `ImportBatch`.

An import batch therefore provides the parent record while `ImportRow` provides row-level processing information.

The row contains:

| Field        | Description                                |
| ------------ | ------------------------------------------ |
| `batch`      | Parent `ImportBatch`                       |
| `row_number` | Spreadsheet row number                     |
| `raw_data`   | Parsed spreadsheet data stored for the row |
| `status`     | Current processing status of the row       |
| `errors`     | Validation errors associated with the row  |

The relationship is:

```text
ImportBatch
    |
    +---- ImportRow
    +---- ImportRow
    +---- ImportRow
    +---- ...
```

Rows belong to their import batch and are processed as part of that batch's lifecycle.

The row-level records allow the API and other application code to identify exactly which spreadsheet rows passed or failed validation without requiring the original spreadsheet to be parsed again solely to inspect stored validation results.

---

# ImportRow Statuses

The row status represents the current processing state of an individual row.

The supported statuses are:

```text
VALID
ERROR
SKIPPED
COMMITTED
```

### `VALID`

The row passed validation.

### `ERROR`

The row contains one or more validation errors.

The details are stored in the row's `errors` field.

### `SKIPPED`

The row was intentionally skipped by the import-processing rules, such as a blank row handled by the parser.

### `COMMITTED`

The row was successfully processed during the commit stage.

---

# Lifecycle

The implemented batch lifecycle is:

```text
UPLOADED
    |
    v
VALIDATING
    |
    +--------------------+
    |                    |
    v                    v
VALIDATED              FAILED
    |                    |
    |                    |
    |                validate again
    |                    |
    |                    v
    |                VALIDATING
    |                    |
    +--------------------+
    |
    v
COMMITTED
```

The available batch statuses are:

```text
UPLOADED
VALIDATING
VALIDATED
FAILED
COMMITTED
```

There is no separate `REVALIDATING` batch status. Revalidation uses the existing `VALIDATING` state.

---

# UPLOADED

A new `ImportBatch` is created when the spreadsheet is uploaded.

At this stage:

* The uploaded file has been stored.
* The batch has been created.
* The spreadsheet is available for processing.
* Destination business tables have not been modified.

The upload operation is preparation for validation rather than an actual business-data import.

Therefore:

```text
UPLOAD
   |
   v
ImportBatch created
   |
   v
No destination business records created
```

---

# VALIDATING

The batch enters `VALIDATING` while its spreadsheet rows are processed.

The generic spreadsheet parser handles spreadsheet structure.

The registered import handler handles domain-specific validation.

During validation:

* Spreadsheet rows are processed.
* `ImportRow` records contain the parsed row data.
* Row-level validation is performed through the registered handler.
* Valid rows are tracked.
* Invalid rows are marked with errors.
* `valid_rows` and `error_rows` are calculated.
* The batch status is updated based on the validation result.

No destination business records are created merely because a row has been parsed or validated.

---

# VALIDATED

A batch becomes `VALIDATED` when the required validation succeeds.

A validated batch is eligible for commit.

This is an important lifecycle rule:

> Only a batch whose current status is `VALIDATED` can be committed.

Validation is therefore a prerequisite for writing imported data into destination business tables.

---

# FAILED

If validation finds row-level errors, the batch is marked `FAILED`.

The failed batch retains its parsed rows and validation errors.

For example:

```text
10 total rows
8 valid rows
2 error rows

Batch status:
FAILED
```

The failed batch is not committed into destination business tables.

The retained `ImportRow` information allows the validation result to be inspected and the validation process to be run again.

---

# Revalidation

A failed batch can be processed through the validation flow again.

Revalidation does not bypass validation.

Instead, the batch returns to the existing `VALIDATING` state and the validation process is executed again.

The lifecycle is therefore:

```text
FAILED
   |
   v
VALIDATING
   |
   +------------------+
   |                  |
   v                  v
FAILED             VALIDATED
                      |
                      v
                   COMMITTED
```

If errors remain, the batch returns to `FAILED`.

If the validation succeeds, the batch becomes `VALIDATED` and can then be committed.

Revalidation must follow the behavior implemented by the current service. The infrastructure should not be interpreted as providing an interactive spreadsheet editor unless such functionality is explicitly implemented elsewhere.

---

# COMMITTED

A `VALIDATED` batch can be committed.

During commit, the registered import handler is responsible for applying the validated rows to the destination business domain.

After a successful commit:

* The batch status becomes `COMMITTED`.
* `committed_at` is recorded.
* Successfully processed rows can be marked `COMMITTED`.
* The import lifecycle is complete.

A committed batch cannot be treated as a new unvalidated batch.

The service enforces the lifecycle state before allowing commit.

---

# Upload and Validation Do Not Modify Destination Tables

The import infrastructure deliberately separates validation from business-data creation.

The following operations do not insert imported records into destination business tables:

```text
Upload
  |
  v
Parse
  |
  v
Create ImportRows
  |
  v
Validate
  |
  v
Revalidate
```

These operations create or update import infrastructure records such as:

* `ImportBatch`
* `ImportRow`

The destination domain is changed only during the explicit commit stage.

Therefore:

```text
UPLOAD       -> no destination change
PARSE        -> no destination change
VALIDATE     -> no destination change
REVALIDATE   -> no destination change
COMMIT       -> destination business changes
```

This separation prevents partially validated spreadsheet data from being written into business tables.

---

# Parser Contract

The generic spreadsheet parser is implemented through `ExcelParser`.

Its responsibility is spreadsheet-level processing.

The parser is responsible for:

* Opening the uploaded Excel file.
* Reading spreadsheet rows.
* Reading spreadsheet headers.
* Extracting row data.
* Handling blank rows according to parser rules.
* Converting spreadsheet values into JSON-safe representations.
* Providing structured row information to the import infrastructure.

The parser is intentionally generic.

It does not know how a particular ESG domain should interpret or persist a row.

For example, `ExcelParser` must not contain logic such as:

```text
Create Answer
Create Datapoint
Create Framework Node
Create Stakeholder
Create Emission Factor
```

Those operations belong to the feature-specific import handler.

The separation is:

```text
ExcelParser
    |
    | spreadsheet structure
    v
ImportBatchService
    |
    | lifecycle orchestration
    v
ImportHandlerRegistry
    |
    | selects handler
    v
Domain Import Handler
    |
    | domain-specific validation/commit
    v
Destination Business Model
```

---

# Handler Extension Contract

Feature-specific import behavior is provided through the `ImportHandler` contract and `ImportHandlerRegistry`.

A future module should implement the domain-specific behavior required for its import type instead of duplicating the generic import infrastructure.

Conceptually, a future handler follows the existing contract:

```python
class ExampleImportHandler(ImportHandler):
    def validate_row(self, row):
        ...

    def validate_batch(self, batch):
        ...

    def commit(self, batch):
        ...
```

The exact implementation depends on the domain.

The important separation is:

### `validate_row()`

Performs validation that applies to an individual spreadsheet row.

Examples:

* Required field validation.
* Datatype validation.
* Reference validation.
* Allowed-value validation.
* Domain-specific business rules.

### `validate_batch()`

Performs validation that requires knowledge of the complete batch.

Examples could include:

* Duplicate detection across rows.
* Cross-row consistency.
* Batch-level reference rules.
* Constraints that cannot be evaluated from one row alone.

A handler does not need batch-level logic if the domain does not require it.

### `commit()`

Applies validated rows to the destination business domain.

This is where the domain-specific business records are created or updated.

The handler must not treat upload or validation as a commit operation.

---

# ImportHandlerRegistry

`ImportHandlerRegistry` maps an `import_type` to the handler responsible for that type.

The relationship is:

```text
import_type
     |
     v
ImportHandlerRegistry
     |
     v
Domain Import Handler
```

For example:

```text
ANSWERS
   |
   v
AnswersImportHandler
```

and:

```text
DATAPOINTS
   |
   v
DatapointsImportHandler
```

The registry allows `ImportBatchService` to remain generic.

Without the registry, the service would have to contain feature-specific branching:

```python
if import_type == "ANSWERS":
    ...
elif import_type == "DATAPOINTS":
    ...
elif import_type == "FRAMEWORK_NODES":
    ...
```

With the registry:

```text
ImportBatchService
       |
       v
ImportHandlerRegistry
       |
       v
Correct handler for import_type
```

This makes the infrastructure extensible without modifying the core lifecycle implementation for every new domain.

---

# How a Future Module Consumes the Infrastructure

A future module does not create its own complete import system.

Instead, it consumes the shared infrastructure by supplying the domain-specific handler.

The integration flow is:

```text
1. Future module defines its import behavior
              |
              v
2. Implement ImportHandler
              |
              +--> validate_row()
              |
              +--> validate_batch() if required
              |
              +--> commit()
              |
              v
3. Register handler with ImportHandlerRegistry
              |
              v
4. Existing ImportBatchService locates the handler
              |
              v
5. Existing ExcelParser processes the spreadsheet
              |
              v
6. Existing ImportRow records track row state
              |
              v
7. Handler validates the rows
              |
              v
8. Batch becomes VALIDATED or FAILED
              |
              v
9. Validated batch can be committed
              |
              v
10. Handler writes to destination business tables
```

The future module therefore provides **domain behavior**, while the import foundation provides **infrastructure and lifecycle management**.

---

# What a Future Module Must Implement

When adding a new import domain, the module should:

1. Define the domain-specific import handler.
2. Implement `validate_row()` for row-level validation.
3. Implement `validate_batch()` if batch-level validation is required.
4. Implement `commit()` for destination business changes.
5. Register the handler with `ImportHandlerRegistry`.
6. Ensure any required module context exists in the Module Registry.
7. Add module-specific tests.
8. Use the existing import-batch infrastructure rather than creating duplicate upload/lifecycle logic.

The module should not recreate generic import functionality.

---

# What Future Modules Do Not Implement

A future domain should not create its own separate implementation of:

* `ImportBatch`
* `ImportRow`
* Generic Excel parsing
* Generic file upload handling
* Generic validation lifecycle
* Generic failed-batch state management
* Generic revalidation lifecycle
* Generic commit-state protection
* Generic row error storage
* Generic import activity logging
* A separate upload/validate/commit lifecycle

These responsibilities already belong to the shared import infrastructure.

The domain-specific module provides the handler.

---

# Future Answers Importer

A future Answers handler could:

* Define the expected spreadsheet fields.
* Validate answer-specific values.
* Resolve the relevant datapoint or question.
* Validate references.
* Reject invalid values.
* Create or update Answer records during commit.

Conceptually:

```text
ANSWERS
   |
   v
AnswersImportHandler
   |
   +--> validate_row()
   |
   +--> validate_batch()
   |
   +--> commit()
   |
   v
Answer business records
```

The generic `ImportBatchService`, `ExcelParser`, `ImportBatch`, and `ImportRow` infrastructure remains unchanged.

The M13 foundation does not by itself mean that production Answer business records can already be imported.

---

# Future Datapoints Importer

A Datapoints handler could:

* Validate datapoint fields.
* Validate datapoint types.
* Validate options where applicable.
* Validate table-column definitions where applicable.
* Resolve datapoint categories.
* Create or update datapoint records during commit.

Conceptually:

```text
DATAPOINTS
   |
   v
DatapointsImportHandler
   |
   +--> validate_row()
   |
   +--> validate_batch()
   |
   +--> commit()
   |
   v
Datapoint business records
```

Again, the shared import infrastructure remains unchanged.

---

# Future Framework Nodes Importer

A Framework Nodes handler could:

* Validate framework-specific fields.
* Validate framework/version references.
* Validate framework node relationships.
* Validate required framework information.
* Create or update framework-domain records during commit.

Conceptually:

```text
FRAMEWORK_NODES
   |
   v
FrameworkNodesImportHandler
   |
   +--> validate_row()
   |
   +--> validate_batch()
   |
   +--> commit()
   |
   v
Framework business records
```

---

# Future Stakeholders Importer

A Stakeholders handler could:

* Validate stakeholder fields.
* Validate stakeholder categories.
* Validate stakeholder types.
* Apply organization-specific rules.
* Create or update stakeholder records during commit.

Conceptually:

```text
STAKEHOLDERS
   |
   v
StakeholdersImportHandler
   |
   +--> validate_row()
   |
   +--> validate_batch()
   |
   +--> commit()
   |
   v
Stakeholder business records
```

---

# Future Emission Factors Importer

An Emission Factors handler could:

* Validate emission-factor fields.
* Validate units.
* Validate categories.
* Validate reporting context.
* Validate required references.
* Create or update emission-factor records during commit.

Conceptually:

```text
EMISSION_FACTORS
   |
   v
EmissionFactorsImportHandler
   |
   +--> validate_row()
   |
   +--> validate_batch()
   |
   +--> commit()
   |
   v
Emission Factor business records
```

---

# Import Type vs Module Code

`import_type` and `module_code` represent different concepts.

## `import_type`

Identifies what kind of import is being processed.

Examples:

```text
ANSWERS
DATAPOINTS
FRAMEWORK_NODES
STAKEHOLDERS
EMISSION_FACTORS
```

The `import_type` is used to locate the appropriate import handler.

## `module_code`

Identifies the ESG_360 module associated with the import when module context is required.

The module code must correspond to a controlled entry in the Module Registry.

Conceptually:

```text
ImportBatch
    |
    +-- import_type
    |       |
    |       v
    |   Import Handler
    |
    +-- module_code
            |
            v
       Module Registry
```

For example, conceptually:

```text
import_type = DATAPOINTS
module_code = energy
```

means that the import is a Datapoint import associated with the registered Energy module.

The import system must not accept arbitrary module codes that do not exist in the controlled Module Registry.

---

# Module Registry Integration

The import infrastructure integrates with the M13 Module Registry.

When `module_code` is provided for an import, it must correspond to a module defined in the controlled `Module` catalog.

The canonical source is:

```text
apps.modules.models.Module
```

The relationship is:

```text
ImportBatch
    |
    +-- module_code
            |
            v
      Module Registry
```

This prevents imports from introducing ad-hoc module identifiers simply because a spreadsheet contains an arbitrary value.

For example, a value such as:

```text
my_custom_module
```

should not become a valid ESG_360 module automatically.

The module must first be formally added to the Module Registry.

---

# API

The import API exposes the common batch lifecycle instead of requiring a separate upload implementation for every domain.

The main operations are:

```text
Create/upload batch
       |
       v
View batch
       |
       v
Validate batch
       |
       v
Inspect validation result
       |
       v
Revalidate if required
       |
       v
Commit validated batch
```

The current import application exposes the batch resource through the import API.

The implemented validation operation follows the batch resource pattern:

```text
POST /api/imports/batches/
POST /api/imports/batches/<batch_id>/validate/
```

The exact available routes should remain aligned with the application's URL configuration.

Future domains should use these shared batch operations rather than creating domain-specific upload and validation endpoints.

---

# Upload Request

A batch upload requires the appropriate import information and an Excel file.

For example, an invalid upload request may result in errors such as:

```json
{
    "file": [
        "An Excel file is required."
    ]
}
```

An unsupported import type may result in an error such as:

```json
{
    "import_type": [
        "Invalid import type."
    ]
}
```

If an import type does not have a registered handler, the request cannot proceed as a usable domain import.

For example:

```json
{
    "import_type": [
        "No import handler is registered for ANSWERS."
    ]
}
```

This protects the system from accepting an import for which no domain-specific processing behavior exists.

---

# Batch Response

A successful batch response exposes the current lifecycle state and processing information.

A representative response is:

```json
{
    "id": "f10b920c-d4f2-43c3-b7b1-c99cbd612e27",
    "import_type": "ANSWERS",
    "file_name": "import_answers_test.xlsx",
    "file_path": "...",
    "status": "VALIDATED",
    "total_rows": 10,
    "valid_rows": 10,
    "error_rows": 0,
    "uploaded_at": "...",
    "committed_at": null
}
```

The exact response fields are determined by the serializer currently exposed by the API.

---

# Validation Response

After validation, the batch response exposes the resulting status and row counts.

For example, when validation succeeds:

```json
{
    "id": "f10b920c-d4f2-43c3-b7b1-c99cbd612e27",
    "status": "VALIDATED",
    "total_rows": 10,
    "valid_rows": 10,
    "error_rows": 0
}
```

When validation finds errors:

```json
{
    "id": "f10b920c-d4f2-43c3-b7b1-c99cbd612e27",
    "status": "FAILED",
    "total_rows": 10,
    "valid_rows": 8,
    "error_rows": 2
}
```

The individual `ImportRow` records contain the row-level validation information needed to identify invalid data.

---

# Commit Protection

Commit is allowed only for a batch currently in `VALIDATED` status.

Therefore:

```text
FAILED
  |
  +---- COMMIT -> rejected

UPLOADED
  |
  +---- COMMIT -> rejected

VALIDATING
  |
  +---- COMMIT -> rejected

VALIDATED
  |
  +---- COMMIT -> allowed

COMMITTED
  |
  +---- COMMIT -> rejected
```

This protects destination tables from unvalidated or incorrectly transitioned imports.

The generic service enforces this rule before invoking the domain handler's commit behavior.

---

# Transaction and Commit Safety

The service uses Django transaction handling around lifecycle operations that modify persistent import state and/or commit business data.

The objective is to prevent a partially completed commit from leaving the system in an inconsistent state.

The important separation is:

```text
Validation
    |
    v
Import infrastructure state
    |
    v
ImportBatch + ImportRow
```

and:

```text
Commit
    |
    v
Domain import handler
    |
    v
Destination business records
```

A successful commit results in:

```text
ImportBatch.status = COMMITTED
ImportBatch.committed_at = commit timestamp
```

If commit fails, the operation must not silently report a successful import.

The transaction boundary is intended to ensure that the commit operation does not leave the import infrastructure reporting success when the business-data operation has failed.

---

# Activity and Audit Considerations

Bulk imports should produce meaningful lifecycle audit events.

Important lifecycle-level events include:

```text
Import uploaded
Import validation started
Import validation completed
Import validation failed
Import revalidated
Import committed
```

These events can answer audit questions such as:

* Who uploaded the import?
* What type of import was performed?
* Which batch was processed?
* When was validation performed?
* Did validation succeed or fail?
* When was the batch committed?
* Who initiated the operation?

The implementation uses the application's existing `ActivityLog` infrastructure rather than creating a separate import-specific audit system.

Bulk imports should not automatically create one global `ActivityLog` event for every parsed spreadsheet row.

For example, a spreadsheet containing 10,000 rows should not automatically result in 10,000 global activity events merely because 10,000 rows were parsed.

The distinction is:

```text
ImportRow
    |
    +--> Row-level validation errors

ActivityLog
    |
    +--> Lifecycle-level import actions
```

This keeps the global audit trail useful and prevents high-volume imports from generating excessive audit noise.

If a future domain requires auditing every individual business-record creation or update, that requirement should be implemented by the domain-specific handler or business service.

---

# Testing Future Import Handlers

A future import domain should test its handler independently from the generic infrastructure and also test the integration with the import pipeline.

At minimum, a future handler should test:

### Row validation

Verify that:

* Valid rows are accepted.
* Required fields are enforced.
* Invalid values produce expected errors.
* Invalid references are rejected.

### Batch validation

Where applicable, verify:

* Duplicate rows are detected.
* Cross-row rules are enforced.
* Batch-level constraints are correctly applied.

### Commit

Verify that:

* Validated rows create/update the correct destination records.
* Invalid batches cannot be committed.
* Transaction failures do not report a successful import.

### Registry integration

Verify that:

* The handler is registered for the expected `import_type`.
* The import service can locate the handler.
* An import without a registered handler is rejected.

The generic import infrastructure tests should continue to verify lifecycle behavior independently of domain-specific business rules.

---

# Example Future Module Integration

A new Datapoints importer would conceptually follow this process:

```text
Step 1
Create DatapointsImportHandler

        |
        v

Step 2
Implement validate_row()

        |
        v

Step 3
Implement validate_batch()
if Datapoint domain requires batch-level validation

        |
        v

Step 4
Implement commit()

        |
        v

Step 5
Register handler for DATAPOINTS

        |
        v

Step 6
Use existing /api/imports/batches/ endpoint

        |
        v

Step 7
Existing infrastructure parses Excel

        |
        v

Step 8
Existing ImportRows store row state

        |
        v

Step 9
DatapointsImportHandler validates rows

        |
        +----------+
        |          |
        v          v
     FAILED    VALIDATED
        |          |
        |          v
        |        COMMIT
        |          |
        |          v
        |    Datapoint records
        |
        +--> validate again
```

No new generic import lifecycle implementation is required.

---

# Current Integration Status

The current M13 implementation provides the **shared import-batch infrastructure**.

Implemented infrastructure includes:

* `ImportBatch`
* `ImportRow`
* Excel file handling
* Generic `ExcelParser`
* `ImportUploadService`
* `ImportBatchService`
* `ImportHandler` contract
* `ImportHandlerRegistry`
* Import lifecycle states
* Row-level validation tracking
* Failed-batch handling
* Revalidation through the validation lifecycle
* Validated-batch commit protection
* Module Registry integration
* Activity logging

The current implementation is intentionally designed as infrastructure rather than as a complete importer for every ESG domain.

---

# Destination Handlers Are Separate Work

Real destination import handlers for domains such as:

```text
Answers
Datapoints
Framework Nodes
Stakeholders
Emission Factors
```

are separate domain-level work unless explicitly implemented and registered.

The import foundation provides the contract those handlers use.

Therefore, completion of the M13 Import Batch foundation must not be interpreted as meaning that every listed domain can already import production business records.

The architecture is:

```text
                 Uploaded File
                      |
                      v
             ImportUploadService
                      |
                      v
                 ImportBatch
                      |
                      v
             ImportBatchService
                      |
          +-----------+-----------+
          |                       |
          v                       v
     ExcelParser        ImportHandlerRegistry
                                  |
                                  v
                         Domain Import Handler
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                    Validation          Commit
                                           |
                                           v
                                  Destination Business
                                      Tables
```

---

# Responsibilities by Layer

| Component               | Responsibility                                    | Domain-specific? |
| ----------------------- | ------------------------------------------------- | ---------------- |
| `ImportUploadService`   | File upload, storage, batch creation              | No               |
| `ImportBatch`           | Batch lifecycle state and metadata                | No               |
| `ImportRow`             | Row data and row-level processing state           | No               |
| `ExcelParser`           | Spreadsheet parsing                               | No               |
| `ImportBatchService`    | Lifecycle orchestration                           | No               |
| `ImportHandlerRegistry` | Handler lookup/registration                       | No               |
| `ImportHandler`         | Domain validation and commit contract             | Yes              |
| Domain Import Handler   | Feature-specific rules and destination operations | Yes              |
| Destination Model       | Actual business data                              | Yes              |
| `ActivityLog`           | Lifecycle-level audit events                      | Shared           |

This separation is the core reason the infrastructure can be reused by future modules.

---

# Adding a New Import Type Checklist

When adding a new domain import, follow this sequence:

1. Define or confirm the required `import_type`.
2. Determine whether a `module_code` is required.
3. Ensure the required module exists in the Module Registry.
4. Implement the domain-specific `ImportHandler`.
5. Implement `validate_row()`.
6. Implement `validate_batch()` if required.
7. Implement `commit()`.
8. Register the handler with `ImportHandlerRegistry`.
9. Add handler-specific tests.
10. Add integration tests for the import lifecycle.
11. Use the existing import-batch API and services.
12. Do not duplicate generic upload, parsing, validation-state, or commit-state logic.

---

# Summary

The M13 Import Batch foundation provides a controlled lifecycle for spreadsheet imports:

```text
UPLOAD
  |
  v
UPLOADED
  |
  v
VALIDATING
  |
  +-----------> FAILED
  |                |
  |                |
  |           validate again
  |                |
  |                v
  |            VALIDATING
  |
  v
VALIDATED
  |
  v
COMMITTED
```

The key architectural rule is:

> Parsing and validation operate on `ImportBatch` and `ImportRow`; destination business tables are modified only during an explicit commit performed through the appropriate domain import handler.

A future module consumes the infrastructure by implementing and registering its domain-specific `ImportHandler`.

The future module supplies:

```text
Domain-specific validation
Domain-specific batch rules
Domain-specific commit logic
```

The shared infrastructure supplies:

```text
File upload
File storage
Excel parsing
ImportBatch
ImportRow
Lifecycle management
Validation orchestration
Row-level error tracking
Revalidation flow
Commit protection
Module Registry integration
Activity logging
```

Therefore, adding a new importer does not require duplicating the entire spreadsheet-import lifecycle.

The intended architecture is:

```text
                    Shared Import Infrastructure
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
        ExcelParser    ImportBatchService   Registry
             |                |                |
             +----------------+----------------+
                              |
                              v
                    Domain Import Handler
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
        Answers        Datapoints       Framework Nodes
             |
             +----------------+----------------+
                              |
                              v
                    Destination Business Tables
```

The M13 foundation therefore provides a reusable import mechanism while keeping domain-specific spreadsheet interpretation and business-data persistence isolated inside the appropriate future module handler.
