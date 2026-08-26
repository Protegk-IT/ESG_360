import type { DatapointDataType } from "@/types/datapoint";
import type {
  M5Answer,
  TypedValueWritePayload,
} from "@/types/dataCapture";

import type { FieldValue } from "@/pages/datapoints/fields";

/* ==========================================================
   BACKEND ANSWER → M4 FIELD VALUE
   ----------------------------------------------------------
   Converts the persisted M5 scalar answer into the value
   representation expected by DynamicFieldRenderer.

   TABLE is intentionally excluded here and handled by the
   TABLE adapter.
========================================================== */

export function answerToFieldValue(
  answer: M5Answer | null | undefined,
  dataType: DatapointDataType,
): FieldValue {
  if (!answer) {
    return getEmptyFieldValue(dataType);
  }

  switch (dataType) {
    case "DECIMAL":
      return normalizeDecimalValue(answer.decimal_value);

    case "INTEGER":
      return answer.integer_value;

    case "TEXT":
    case "LONG_TEXT":
      return answer.text_value ?? "";

    case "BOOLEAN":
      return answer.boolean_value ?? false;

    case "SELECT":
      return answer.selected_option ?? "";

    case "DATE":
      return answer.date_value ?? "";

    case "TABLE":
      // TABLE values are normalized separately through
      // tableAnswerAdapter.ts.
      return [];

    default:
      return null;
  }
}

/* ==========================================================
   M4 FIELD VALUE → M5 TYPED WRITE PAYLOAD
   ----------------------------------------------------------
   Converts the value emitted by DynamicFieldRenderer into
   the exact typed fields expected by M5.

   No generic `value` field is ever sent.
========================================================== */

export function fieldValueToAnswerPayload(
  dataType: DatapointDataType,
  value: FieldValue,
  unitId?: string | null,
): TypedValueWritePayload {
  switch (dataType) {
    case "DECIMAL":
      return {
        decimal_value:
          typeof value === "number" ? value : null,
        unit: unitId ?? null,
      };

    case "INTEGER":
      return {
        integer_value:
          typeof value === "number" ? value : null,
        unit: unitId ?? null,
      };

    case "TEXT":
    case "LONG_TEXT":
      return {
        text_value:
          typeof value === "string" ? value : "",
      };

    case "BOOLEAN":
      return {
        boolean_value: value === true,
      };

    case "SELECT":
      return {
        selected_option:
          typeof value === "string" && value.length > 0
            ? value
            : null,
      };

    case "DATE":
      return {
        date_value:
          typeof value === "string" && value.length > 0
            ? value
            : null,
      };

    case "TABLE":
      throw new Error(
        "TABLE values must be handled by tableAnswerAdapter.ts.",
      );

    default:
      return {};
  }
}

/* ==========================================================
   EMPTY FIELD VALUE
   ----------------------------------------------------------
   Matches the initial values used by DynamicFieldRenderer.
========================================================== */

function getEmptyFieldValue(
  dataType: DatapointDataType,
): FieldValue {
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
   DECIMAL NORMALIZATION
   ----------------------------------------------------------
   Django/DRF DecimalField responses may arrive as strings
   depending on the API/client serialization.

   M4 numeric fields expect number | null.
========================================================== */

function normalizeDecimalValue(
  value: number | string | null,
): number | null {
  if (value === null) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  const numericValue = Number(value);

  return Number.isFinite(numericValue)
    ? numericValue
    : null;
}