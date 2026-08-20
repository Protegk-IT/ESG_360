# Datapoint Catalog

M4 defines the datapoint catalog and unit registry. It answers what can be
measured, how it should be represented, which unit metadata applies, and what
validation hints downstream capture flows should use. M4 does not store answers,
submissions, evidence, calculations, or framework mappings.

## Model Relationships

```text
UnitFamily
  -> Unit

Module
  -> DatapointCategory
       -> Datapoint
            -> DatapointOption
            -> DatapointTableColumn
            -> DatapointTableRow
```

- `UnitFamily` groups compatible units such as energy, mass, or volume.
- `Unit` belongs to one family and carries a deterministic conversion factor to
  that family's base unit.
- `DatapointCategory` belongs to one Module Registry `Module`.
- `Datapoint` belongs to one category and one Module Registry `Module`.
- A datapoint's `module` must match its category's `module`.
- `DatapointOption` is valid only for `SELECT` datapoints.
- `DatapointTableColumn` and `DatapointTableRow` are valid only for `TABLE`
  datapoints.

## Supported Types

The supported `Datapoint.data_type` values are:

```text
DECIMAL
INTEGER
TEXT
LONG_TEXT
BOOLEAN
SELECT
DATE
TABLE
```

`DECIMAL` and `INTEGER` datapoints may declare `unit_family` and
`default_unit`. Text, boolean, select, date, and table datapoints must not carry
unit metadata.

`SELECT` values must come from `DatapointOption`; clients should not hardcode
option lists.

## Validation Metadata Contract

`Datapoint.validation_metadata` and
`DatapointTableColumn.validation_metadata` are JSON objects. They are the M4
contract for definition-driven value validation in M5.

Examples:

```json
{"min": "0", "decimal_places": 4}
```

```json
{"max_length": 255}
```

M4 stores this metadata but does not validate submitted values because submitted
values are outside the M4 boundary.

## TABLE Contract

A `TABLE` datapoint defines a structured input. M4 stores the definition only:

```text
Datapoint(data_type=TABLE)
  -> table_columns
  -> table_rows
```

Each `DatapointTableColumn` includes:

```text
code
label
data_type
unit_family
default_unit
is_required
validation_metadata
display_order
```

Table columns may use the same scalar data types as normal datapoints except
`TABLE`; nested tables are not part of M4. Column unit rules match normal
datapoints: only `DECIMAL` and `INTEGER` columns may use a unit family, and a
default unit must belong to that family.

Each `DatapointTableRow` includes:

```text
code
label
display_order
```

Within a single table datapoint, column codes, column display orders, row codes,
and row display orders are unique.

Dynamic row capability is explicit:

```text
allow_dynamic_rows = false
```

means the catalog rows are fixed. M5 should render only the predefined
`DatapointTableRow` records.

```text
allow_dynamic_rows = true
```

means M5 may allow users to add rows during data capture. Those user-added rows
are not M4 catalog rows.

## Unit Conversion Contract

Each `Unit` has:

```text
family
code
name
factor_to_base
is_base_unit
is_active
```

Conversion to the family base unit is deterministic Decimal multiplication:

```text
base_value = value * factor_to_base
```

Unit invariants:

- `factor_to_base` must be greater than zero.
- A base unit must have `factor_to_base = 1`.
- Only one base unit may exist per family.
- A datapoint or table column default unit must belong to the selected family.

## API Examples

List datapoints:

```http
GET /api/datapoints/?module=energy
GET /api/datapoints/?category={category_id}
GET /api/datapoints/?data_type=SELECT
GET /api/datapoints/?is_active=true
```

Retrieve a datapoint definition:

```http
GET /api/datapoints/{id}/
```

Example shape:

```json
{
  "id": "cdc7c506-3530-4d53-96aa-05d4f4524534",
  "code": "ENERGY_TOTAL_CONSUMPTION",
  "category": {
    "code": "ENERGY_CONSUMPTION",
    "module": "energy"
  },
  "module": "energy",
  "label": "Total energy consumption",
  "data_type": "DECIMAL",
  "unit_family": {
    "code": "ENERGY"
  },
  "default_unit": {
    "code": "KWH",
    "factor_to_base": "1.0000000000"
  },
  "collection_level": "ORG_NODE",
  "frequency": "MONTHLY",
  "is_required": false,
  "allow_dynamic_rows": false,
  "validation_metadata": {
    "min": "0",
    "decimal_places": 4
  },
  "options": [],
  "table_columns": [],
  "table_rows": []
}
```

Fetch select options:

```http
GET /api/datapoints/{id}/options/
```

Fetch a table definition:

```http
GET /api/datapoints/{id}/table-definition/
```

Example shape:

```json
{
  "datapoint": {
    "code": "EMISSIONS_TABLE",
    "data_type": "TABLE",
    "allow_dynamic_rows": false
  },
  "columns": [
    {
      "code": "SOURCE",
      "label": "Emission Source",
      "data_type": "TEXT",
      "is_required": true,
      "validation_metadata": {
        "max_length": 255
      },
      "display_order": 1
    }
  ],
  "rows": [
    {
      "code": "SCOPE_1",
      "label": "Scope 1",
      "display_order": 1
    }
  ]
}
```

Administrative writes require `datapoint.manage`. Authenticated users may read
catalog definitions.

## Adding Datapoints Safely

1. Seed or confirm the target module in the Module Registry.
2. Create or reuse a category in the same module.
3. Choose one canonical `data_type`.
4. Add units only to `DECIMAL` or `INTEGER` definitions.
5. Add `validation_metadata` as a JSON object when M5 needs validation hints.
6. For `SELECT`, add `DatapointOption` rows instead of frontend constants.
7. For `TABLE`, add `DatapointTableColumn` rows, optional fixed
   `DatapointTableRow` rows, and set `allow_dynamic_rows` explicitly.
8. Add or update definitions in `seed_datapoints` so the catalog is repeatable.
9. Run the datapoint tests and seed command repeatedly to confirm idempotency.

M4 must stay limited to catalog definitions. Answer capture, submissions,
evidence, calculations, and framework mapping belong to later milestones.
