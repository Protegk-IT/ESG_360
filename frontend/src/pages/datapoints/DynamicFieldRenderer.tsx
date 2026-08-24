import type { DatapointDataType, DatapointDetail, Unit } from "@/types/datapoint";

import {
  DecimalField,
  IntegerField,
  TextField,
  LongTextField,
  BooleanField,
  SelectField,
  DateField,
  TableField,
  type FieldValue,
} from "./fields";

/* ==========================================================
   INITIAL VALUE PER TYPE
   ----------------------------------------------------------
   Ensures every field starts life as a controlled component
   (never undefined → avoids the classic React "changing an
   uncontrolled input to controlled" warning) with a type-
   appropriate empty state.

   Only applied when `value` is `undefined` (never set). An
   explicit `null` (e.g. a numeric field the user cleared) is
   left as-is and NOT overwritten by this default.
========================================================== */

function getInitialValueForType(dataType: DatapointDataType): FieldValue {
  switch (dataType) {
    case "DECIMAL":
    case "INTEGER":
      return null;
    case "TEXT":
    case "LONG_TEXT":
    case "SELECT":
    case "DATE":
      return "";
    case "BOOLEAN":
      return false;
    case "TABLE":
      return [];
    default:
      return null;
  }
}

/* ==========================================================
   PROPS
   ----------------------------------------------------------
   required / readOnly / error are optional per-field state
   overrides a parent form can pass in for a given datapoint
   instance (e.g. a conditionally-required field, a field
   locked after submission, or a validation error message).
========================================================== */

export interface DynamicFieldRendererProps {
  datapoint: DatapointDetail;
  value: FieldValue;
  onChange: (value: FieldValue) => void;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  error?: string | null;
  /** Resolved Unit objects keyed by Unit ID, for numeric fields/cells
   *  that have a unit family. Optional — omitted callers see no unit
   *  suffix, same as before this change. */
  unitsById?: Record<string, Unit>;
}

/* ==========================================================
   DYNAMIC FIELD RENDERER
   ----------------------------------------------------------
   Maps backend DatapointDataType to the correct frontend
   field component, and normalizes shared field state
   (required / error / disabled / readOnly / initial value)
   across all of them.

   Backend-supported types:
   DECIMAL, INTEGER, TEXT, LONG_TEXT, BOOLEAN, SELECT, DATE, TABLE
========================================================== */

export function DynamicFieldRenderer({
  datapoint,
  value,
  onChange,
  disabled = false,
  readOnly = false,
  required,
  error = null,
  unitsById,
}: DynamicFieldRendererProps) {
  // Only fills in a default when the value was never set at
  // all. An explicit null/"" from the caller is respected.
  const resolvedValue =
    value === undefined ? getInitialValueForType(datapoint.data_type) : value;

  const sharedProps = {
    datapoint,
    disabled,
    readOnly,
    required,
    error,
  } as const;

  switch (datapoint.data_type) {
    /* ======================================================
       DECIMAL
    ====================================================== */

     case "DECIMAL":
      return (
        <DecimalField
          {...sharedProps}
          value={typeof resolvedValue === "number" ? resolvedValue : null}
          onChange={(newValue) => onChange(newValue)}
          unitsById={unitsById}
        />
      );

    /* ======================================================
       INTEGER
    ====================================================== */

     case "INTEGER":
      return (
        <IntegerField
          {...sharedProps}
          value={typeof resolvedValue === "number" ? resolvedValue : null}
          onChange={(newValue) => onChange(newValue)}
          unitsById={unitsById}
        />
      );

    /* ======================================================
       TEXT
    ====================================================== */

    case "TEXT":
      return (
        <TextField
          {...sharedProps}
          value={typeof resolvedValue === "string" ? resolvedValue : ""}
          onChange={(newValue) => onChange(newValue)}
        />
      );

    /* ======================================================
       LONG TEXT
    ====================================================== */

    case "LONG_TEXT":
      return (
        <LongTextField
          {...sharedProps}
          value={typeof resolvedValue === "string" ? resolvedValue : ""}
          onChange={(newValue) => onChange(newValue)}
        />
      );

    /* ======================================================
       BOOLEAN
    ====================================================== */

    case "BOOLEAN":
      return (
        <BooleanField
          {...sharedProps}
          value={resolvedValue === true}
          onChange={(newValue) => onChange(newValue)}
        />
      );

    /* ======================================================
       SELECT
       ------------------------------------------------------
       Options come from datapoint.options (DatapointOption).
    ====================================================== */

    case "SELECT":
      return (
        <SelectField
          {...sharedProps}
          value={typeof resolvedValue === "string" ? resolvedValue : ""}
          onChange={(newValue) => onChange(newValue)}
        />
      );

    /* ======================================================
       DATE
    ====================================================== */

    case "DATE":
      return (
        <DateField
          {...sharedProps}
          value={typeof resolvedValue === "string" ? resolvedValue : ""}
          onChange={(newValue) => onChange(newValue)}
        />
      );

    /* ======================================================
       TABLE
       ------------------------------------------------------
       Table definition comes from datapoint.table_columns /
       datapoint.table_rows (DatapointTableColumn / Row).
    ====================================================== */

      case "TABLE":
      return (
        <TableField
          {...sharedProps}
          value={Array.isArray(resolvedValue) ? resolvedValue : []}
          onChange={(newValue) => onChange(newValue)}
          unitsById={unitsById}
        />
      );

    /* ======================================================
       SAFETY FALLBACK
    ====================================================== */

    default:
      return null;
  }
}