import type { DatapointDataType, ValidationMetadata } from "@/types/datapoint";

export type CellPrimitive = string | number | boolean | null;

/* ==========================================================
   SHARED VALIDATION
   ----------------------------------------------------------
   Single source of truth for what a column/datapoint's
   validation_metadata means, keyed by data_type. Used by:
     - DataCell / TableField in fields.tsx (per-cell validation
       and dynamic row-count validation in the active TABLE
       renderer)
     - anywhere else that needs to check a value against rules
   without re-deriving the same switch statement.
========================================================== */


export function validateValue(
  dataType: DatapointDataType,
  rules: ValidationMetadata,
  value: CellPrimitive,
  isRequired: boolean
): string | null {
  const isEmpty = value === null || value === undefined || value === "";

  if (isEmpty) {
    return isRequired ? "This field is required." : null;
  }

  switch (dataType) {
    case "DECIMAL":
    case "INTEGER": {
      const num = typeof value === "number" ? value : Number(value);
      if (Number.isNaN(num)) return "Must be a number.";
      if (dataType === "INTEGER" && !Number.isInteger(num)) {
        return "Must be a whole number.";
      }
      if (typeof rules.min === "number" && num < rules.min) {
        return `Must be at least ${rules.min}.`;
      }
      if (typeof rules.max === "number" && num > rules.max) {
        return `Must be at most ${rules.max}.`;
      }
      if (dataType === "DECIMAL" && typeof rules.decimal_places === "number") {
        const [, decimals = ""] = String(num).split(".");
        if (decimals.length > rules.decimal_places) {
          return `Must have at most ${rules.decimal_places} decimal place${
            rules.decimal_places === 1 ? "" : "s"
          }.`;
        }
      }
      return null;
    }

    case "TEXT":
    case "LONG_TEXT": {
      const str = String(value);
      if (typeof rules.min_length === "number" && str.length < rules.min_length) {
        return `Must be at least ${rules.min_length} characters.`;
      }
      if (typeof rules.max_length === "number" && str.length > rules.max_length) {
        return `Must be at most ${rules.max_length} characters.`;
      }
      if (typeof rules.pattern === "string" && rules.pattern !== "") {
        try {
          const re = new RegExp(rules.pattern);
          if (!re.test(str)) return "Does not match the required format.";
        } catch {
          // Malformed regex stored on the column — a config problem, not
          // something to block the user's answer on. Skip silently.
        }
      }
      return null;
    }

    case "DATE": {
      const str = String(value);
      if (typeof rules.min_date === "string" && str < rules.min_date) {
        return `Must be on or after ${rules.min_date}.`;
      }
      if (typeof rules.max_date === "string" && str > rules.max_date) {
        return `Must be on or before ${rules.max_date}.`;
      }
      return null;
    }

    // BOOLEAN / SELECT have no rule surface today.
    case "BOOLEAN":
    case "SELECT":
    default:
      return null;
  }
}

/** Checks a TABLE's dynamic row count against min_rows/max_rows. Meaningless
 *  (and never called) for fixed-row tables, where the row set is closed. */
export function validateRowCount(
  rowCount: number,
  rules: ValidationMetadata
): string | null {
  if (typeof rules.min_rows === "number" && rowCount < rules.min_rows) {
    return `At least ${rules.min_rows} row${rules.min_rows === 1 ? "" : "s"} required.`;
  }
  if (typeof rules.max_rows === "number" && rowCount > rules.max_rows) {
    return `No more than ${rules.max_rows} row${rules.max_rows === 1 ? "" : "s"} allowed.`;
  }
  return null;
}