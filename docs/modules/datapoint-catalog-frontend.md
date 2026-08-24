# M4 Datapoint Catalog frontend

The M4 frontend exposes the canonical catalog under `/datapoints`. It consumes
definitions; it does not store captured ESG values or duplicate M4 validation
rules.

## Routes and access

Authenticated users can browse `/datapoints` and `/datapoints/:id`. Catalog
reads are deliberately not gated by a made-up `datapoint.view` permission.
Create, edit, categories, units, SELECT options, and TABLE-definition routes
require the canonical `datapoint.manage` permission (superusers bypass it).
The sidebar always exposes **Datapoint Catalog** to an authenticated user, and
exposes management links only to `datapoint.manage` users.

## Definition contract

The forms preserve all current M4 fields: eight datapoint types (`DECIMAL`,
`INTEGER`, `TEXT`, `LONG_TEXT`, `BOOLEAN`, `SELECT`, `DATE`, `TABLE`), module,
category, `COMPANY`/`ORG_NODE`/`FACILITY`/`ANY` collection level, unit family,
default unit, `allow_dynamic_rows`, required state, and `validation_metadata`.
Only supported M4 metadata is surfaced by the renderer: numeric `min`, `max`,
and `decimal_places`; text `max_length`; and TABLE `min_rows`.

`SELECT` datapoints use `DatapointOption`. A TABLE column cannot be `SELECT`
in the management UI. Existing/legacy SELECT TABLE columns render a disabled
unsupported message: M4 currently has no column-option catalog, and M5 safely
rejects supplied SELECT-table-cell values.

## Dynamic renderer and M5 adapter

`DynamicFieldRenderer` dispatches every supported scalar type and `TABLE` to
the shared `TableField`. It accepts `disabled`, `readOnly`, `required`, error,
and optional unit lookup state, so M5 can reuse the visual renderer without
making it an API client.

Its TABLE state is `TableAnswerDraft` from
`frontend/src/pages/datapoints/tableAnswerAdapter.ts`:

```ts
{
  id: string,                    // client key or persisted M5 row UUID
  definition_row: string | null, // fixed M4 row UUID; null for dynamic rows
  label: string,                 // required for a dynamic row
  display_order: number,
  cells: [{
    column: string,              // M4 table-column UUID
    decimal_value?, integer_value?, text_value?, boolean_value?, date_value?,
    unit?                        // M4 Unit UUID for numeric values
  }]
}
```

`toM5TableRowPayload` converts one row directly to M5’s normalized TABLE-row
write body. Fixed rows retain `definition_row`; user-added rows use `null`, a
label, and a display order. The adapter deliberately uses UUIDs instead of
codes, so an M5 entry screen does not need fragile code lookups.

## Verification

Run `npm ci`, `npm run build`, and `npm run lint` from `frontend/`. Browser
smoke coverage should include read-only catalog browsing, `datapoint.manage`
administration, SELECT options, units, fixed/dynamic TABLE definitions and
renderer validation/error/disabled states.
