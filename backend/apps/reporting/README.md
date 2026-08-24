# Reporting value resolution

`ReportValueResolver.build_dataset(report_run)` resolves a frozen M8 `ReportRun` through its immutable `SnapshotMapping` records. The captured-value provider reads only M5 `DataRequest` records whose submission is `APPROVED` and whose reporting period matches the run.

## Output contract

Each mapping produces one or more ordered values. Multiple approved values remain separate by `org_node_id`; M8 does not aggregate them.

```json
{
  "snapshot_node_id": "...",
  "snapshot_mapping_id": "...",
  "canonical_datapoint_code": "ENERGY_TOTAL",
  "status": "RESOLVED",
  "data_type": "DECIMAL",
  "value": 125.5,
  "unit": {"id": "...", "code": "KWH", "name": "Kilowatt-hour"},
  "data_request_id": "...",
  "submission_id": "...",
  "answer_id": "...",
  "org_node_id": "...",
  "org_node_name": "Plant A",
  "provenance": {
    "source_type": "CAPTURED",
    "approved_by": {"id": "...", "username": "reviewer", "name": "Reviewer"},
    "approved_at": "...",
    "entered_by": {"id": "...", "username": "maker", "name": "Maker"}
  }
}
```

Scalar values preserve the M5 typed representation for DECIMAL, INTEGER, TEXT, LONG_TEXT, BOOLEAN, SELECT, and DATE. SELECT values include option identity, code, and label. TABLE values preserve rows, fixed-row identity or dynamic labels, row order, column identity, typed cell values, and cell units.

A mapping without an approved value returns `status: UNRESOLVED` and `value: null`. Draft, submitted, rejected, and reopened-but-not-approved submissions are excluded. Resolution never writes M5 records.

## API

Authenticated clients can read the dataset at:

`GET /api/reporting/report-runs/{id}/resolved-values/`

The report run must be frozen. The response contains `report_run_id`, frozen status, and an ordered `values` array. The endpoint is read-only.

## Provider boundary

`CapturedValueProvider` is the current M5 provider. A future M6 provider can implement the same mapping-to-resolved-value boundary without changing the frozen M8 snapshot or captured-value contract. M8 does not execute calculations or aggregate values.

PDF, Excel, templates, final rendering, and export remain later reporting work.
