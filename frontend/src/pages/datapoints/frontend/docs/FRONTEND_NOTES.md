# M4 — Frontend Catalog & Dynamic Field Renderer: Handover Notes

Scope: this document covers what shipped in
`25-m4-frontend-catalog-and-dynamic-field-renderer`. It is a frontend-only
reference — no backend behavior is described or assumed beyond what M4/M5
already expose.

---

## 1. Routes / Screens

All datapoint-related routes live in `App.tsx`. Permission gating uses
`ProtectedRoute`; when `permission` is omitted, any authenticated user may
access the route (no specific permission required beyond being logged in).

| Route | Screen | Permission |
|---|---|---|
| `/datapoints` | `DatapointList` — catalog browse/search/filter | authenticated (any user) |
| `/datapoints/:id` | `DatapointDetailPage` — read-only detail + live field preview | authenticated (any user) |
| `/datapoints/create` | `DatapointCreate` | `datapoint.manage` |
| `/datapoints/:id/edit` | `DatapointEdit` | `datapoint.manage` |
| `/datapoints/:id/options` | `DatapointOptionsManager` — SELECT datapoint options | `datapoint.manage` |
| `/datapoints/:id/table-definition` | `DatapointTableDefinitionManager` — TABLE columns/rows | `datapoint.manage` |
| `/units/families` | `UnitFamilyManager` | `datapoint.manage` |
| `/units` | `UnitManager` | `datapoint.manage` |
| `/datapoints/categories` | `CategoryManager` | `datapoint.manage` |

**Sidebar:** `sidebar-data.ts` mirrors this split — "Datapoint Catalog"
has no `permission` field (visible to all authenticated users); "Units
Manager" and "Category Manager" require `datapoint.manage`.
`AppSidebar.tsx`'s `canAccess()` treats an omitted `permission` as
"authenticated is enough," matching `ProtectedRoute`.

**Read-only UI:** `DatapointList` and `DatapointDetailPage` compute
`canManage = user?.is_superuser || permissions.includes("datapoint.manage")`
and hide Add/Edit controls (list toolbar, row action menu, detail page
Edit button) when `false`. View/browse is never restricted.

---

## 2. Dynamic Renderer Contract

Entry point: `DynamicFieldRenderer` (`DynamicFieldRenderer.tsx`).

```ts
interface DynamicFieldRendererProps {
  datapoint: DatapointDetail;
  value: FieldValue;
  onChange: (value: FieldValue) => void;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;     // overrides datapoint.is_required if provided
  error?: string | null;  // overrides internal validation if provided
  unitsById?: Record<string, Unit>; // resolved Unit objects, keyed by Unit ID
}
```

`FieldValue = string | number | boolean | Record<string, unknown>[] | null | undefined`

Dispatch is a straight switch on `datapoint.data_type`
(`DECIMAL | INTEGER | TEXT | LONG_TEXT | BOOLEAN | SELECT | DATE | TABLE`)
to one component per type, all defined in `fields.tsx`:
`DecimalField`, `IntegerField`, `TextField`, `LongTextField`,
`BooleanField`, `SelectField`, `DateField`, `TableField`.

**Validation:** every field component now self-validates against
`datapoint.validation_metadata` via `validateValue()`
(`TableDatapointvalidation.ts`) whenever the caller doesn't pass an
explicit `error` prop (`error ?? validateValue(...)`). A parent form can
still override with its own error (e.g. a server-side error after
submit) by passing `error` directly — that always wins.

**Units:** `unitsById` is optional and additive. When present and the
datapoint (or, for TABLE, a column) has a `default_unit` matching a key
in `unitsById`, the resolved `Unit.code` renders next to the numeric
input. Omitted entirely → no unit suffix, same as pre-M4 behavior.

**Caller responsibility:** the renderer does not fetch anything itself.
`DatapointDetailPage` shows the reference pattern — it fetches
SELECT options / TABLE definition on demand (see §5) and resolves
`unitsById` via `DatapointApi.getUnitsByFamily()` for every unit family
referenced by the datapoint or its table columns.

---

## 3. TABLE State Shape

Defined and documented inline in `fields.tsx` above `TableField`.

```ts
type TableRowValue = Record<string, unknown> & {
  id?: string;               // stable client key
  row_code?: string | null;  // DatapointTableRow.code for fixed rows; null for dynamic
  is_dynamic?: boolean;
  [columnCode: string]: unknown; // one key per DatapointTableColumn.code
};

// The datapoint's value is TableRowValue[]
```

This is intentionally **flat**, not nested (`{ row, cells: [...] }`).
Every piece of information an M5 `AnswerTableRow`/`AnswerTableCell` pair
needs is present and separable — see §6.

---

## 4. Fixed vs Dynamic Rows

- **Fixed rows** come from `datapoint.table_rows` (`DatapointTableRow[]`,
  backend-defined, sorted by `display_order`). Their identity is
  `row_code = DatapointTableRow.code`, and their client `id` is always
  `` `fixed:${row.code}` ``. Fixed rows always render, in
  `display_order`, whether or not the user has entered any value yet
  (an empty fixed row still shows in the table with blank cells).
- **Dynamic rows** exist only when `datapoint.allow_dynamic_rows` is
  `true`. They have `is_dynamic: true`, `row_code: null`, and a
  generated `id` (`crypto.randomUUID()`, or a timestamp-based fallback
  if `crypto.randomUUID` is unavailable). They render after all fixed
  rows, labeled `Row 1`, `Row 2`, … by position, and can be removed
  individually (fixed rows cannot be removed from this screen — row
  definition is managed separately via `DatapointTableDefinitionManager`).
- `validateRowCount()` (dynamic-row count against
  `validation_metadata.min_rows`/`max_rows`) is only ever invoked when
  `allow_dynamic_rows` is true — meaningless for a closed, fixed-row set.

---

## 5. M4 API Assumptions

The frontend assumes the following endpoints/shapes exist as currently
implemented (all via `DatapointApi`):

- `getAll()`, `getById(id)` — base `Datapoint` fields only (no nested
  relations).
- `getCategories()`, `getUnitFamilies()`, `getUnitsByFamily(familyId)` —
  used both by admin management screens and by `DatapointDetailPage`'s
  unit-resolution effect.
- `getOptions(datapointId)` — `DatapointOption[]` for a SELECT datapoint.
  Fetched lazily by `DatapointDetailPage` only when
  `data_type === "SELECT"` and `options` isn't already populated.
- `getTableDefinition(datapointId)` → `{ datapoint, columns, rows }` —
  fetched lazily when `data_type === "TABLE"`.
- `getTableColumns(id)` / `getTableRows(id)` — used by
  `DatapointTableDefinitionManager` for column/row CRUD.
- Table column CRUD (`createTableColumn`, `updateTableColumn`,
  `deleteTableColumn`) and row CRUD equivalents.
- `ModuleApi.getEnabled()` — for the module filter on `DatapointList`.

**Known gap (see §7):** there is no endpoint or field providing a
canonical option list for a SELECT-typed *table column* — unlike a
top-level SELECT `Datapoint`, which has `DatapointOption` rows.
`DatapointTableColumn` has no `options` field.

---

## 6. M5 Consumption / Adapter Contract

M5's normalized shapes are (per the merged M5 backend):

- `AnswerTableRow` — one row of an answer: a link to a fixed
  `DatapointTableRow` (or none, for a dynamic row) plus an ordinal.
- `AnswerTableCell` — one cell: row reference + column reference + typed
  value.

The flat `TableRowValue` this frontend produces maps onto that pair
without requiring any change to `TableField`/`DataCell`:

| `TableRowValue` field | Maps to |
|---|---|
| `id` | Not sent to backend directly; client-only row identity |
| `row_code` | `AnswerTableRow.row` (FK to `DatapointTableRow`, resolved by code) — `null` for dynamic rows |
| `is_dynamic` | Determines whether `AnswerTableRow.row` is set or null |
| every other key (`[columnCode]: value`) | One `AnswerTableCell` per key: `{ row: <this row>, column: <resolved DatapointTableColumn by code>, value: <the value> }` |

An M5 adapter layer (not yet built — out of scope for #25 per the
explicit instruction not to start M5 data-entry work here) would:
1. Iterate `TableRowValue[]`.
2. For each row, resolve `row_code` → the matching `DatapointTableRow.id`
   (or omit the FK for a dynamic row).
3. For each column-code key in that row, resolve the code → the matching
   `DatapointTableColumn.id`, and emit one `AnswerTableCell`.

No renderer changes are required to support this — the adapter operates
purely on the existing state shape.

---

## 7. SELECT TABLE-Column Limitation

**Cannot create:** `DatapointTableDefinitionManager`'s column
Data-Type dropdown (`COLUMN_DATA_TYPE_OPTIONS`) intentionally excludes
`SELECT`. A table column can be `DECIMAL`, `INTEGER`, `TEXT`,
`LONG_TEXT`, `BOOLEAN`, or `DATE` only.

**Why:** `DatapointOption` (the model backing scalar SELECT choices) has
a `ForeignKey` to `Datapoint`, not to `DatapointTableColumn`. There is no
model or endpoint today that supplies an option list scoped to a table
column. The merged M5 backend rejects SELECT table cells outright, so
allowing creation of a SELECT column would produce a column that can
never be validly filled.

**Rendering existing/legacy SELECT columns:** if a `SELECT`-typed table
column exists in data from before this restriction (or is created by
another path), `DataCell` in `fields.tsx` renders it as an explicitly
**disabled** input with placeholder text `"Not available — column has
no option data"` — never as an editable free-text box, and never as a
fabricated dropdown with invented options.

**To lift this limitation:** M4 needs a canonical table-column option
contract — e.g. a `DatapointTableColumn.options` field or a sibling
model mirroring `DatapointOption` but scoped to
`DatapointTableColumn`. Once that exists, re-add `"SELECT"` to
`COLUMN_DATA_TYPE_OPTIONS` and replace the disabled-input branch in
`DataCell` with a real `<Select>`.

---

## 8. Build / Lint / Browser Verification

Run before every PR:

```bash
npm ci
npm run build
npm run lint
git diff --check
```

**Browser verification checklist** (admin user + a read-only
authenticated user, two separate sessions):

- [ ] Non-manager: `/datapoints` and `/datapoints/:id` load normally;
      sidebar shows "Datapoint Catalog" but not "Units Manager" /
      "Category Manager".
- [ ] Non-manager: direct navigation to `/datapoints/create`,
      `/datapoints/:id/edit`, `/datapoints/:id/options`,
      `/datapoints/:id/table-definition`, `/units/families`, `/units`,
      `/datapoints/categories` all show Access Denied.
- [ ] Non-manager: list toolbar has no "Add Datapoint" button; row menu
      has "View" only, no "Edit"; detail page has no "Edit Datapoint"
      button.
- [ ] Manager/superuser: all of the above are fully available (no
      regression).
- [ ] Table-definition manager: Add/Edit Column dropdown never offers
      "Select".
- [ ] Detail page field preview: a TABLE datapoint with a legacy
      SELECT column renders that cell as disabled placeholder text,
      never an editable input.
- [ ] Fixed rows render in `display_order` with correct labels; dynamic
      rows can be added/removed (only when `allow_dynamic_rows` is
      true); removing a dynamic row does not affect fixed rows.
- [ ] Numeric datapoint/table cell with a `default_unit` set shows the
      unit code next to the input.
- [ ] Validation: an out-of-range or required-but-empty scalar/table
      value shows the expected message; dynamic-row count violations
      (`min_rows`/`max_rows`) show under the table.
- [ ] Regression: Company, Organization, Users, Reporting Periods,
      Materiality screens and navigation are unaffected by this branch.