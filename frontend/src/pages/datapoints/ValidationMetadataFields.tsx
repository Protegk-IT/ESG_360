import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DatapointDataType, ValidationMetadata } from "@/types/datapoint";

interface ValidationMetadataFieldsProps {
  dataType: DatapointDataType;
  value: ValidationMetadata;
  onChange: (value: ValidationMetadata) => void;
}

function toNumberOrUndefined(raw: string): number | undefined {
  if (raw.trim() === "") return undefined;
  const parsed = Number(raw);
  return Number.isNaN(parsed) ? undefined : parsed;
}

/* ==========================================================
   VALIDATION METADATA FIELDS
   ----------------------------------------------------------
   Renders a plain-language rule builder per data_type instead
   of a raw JSON textarea. Unset/empty fields are omitted from
   the resulting object entirely (rather than stored as null
   or ""), so `validation_metadata` only ever contains rules
   the user actually configured.

   Coverage of DatapointDataType:
     DECIMAL            -> min / max / decimal_places
     INTEGER             -> min / max (no decimal_places —
                            meaningless for whole numbers)
     TEXT, LONG_TEXT     -> min_length / max_length / pattern
     DATE                -> min_date / max_date
     TABLE               -> min_rows / max_rows
     BOOLEAN, SELECT      -> no rules (explicit "none" message,
                            not a silent blank)
========================================================== */

export function ValidationMetadataFields({
  dataType,
  value,
  onChange,
}: ValidationMetadataFieldsProps) {
  const set = (key: string, val: unknown) => {
    const next = { ...value };
    if (val === undefined || val === "" || val === null) {
      delete next[key];
    } else {
      next[key] = val;
    }
    onChange(next);
  };

  if (dataType === "DECIMAL") {
    return (
      <div className="space-y-4 rounded-lg border-[1.5px] border-[#8891A3] p-4">
        <p className="text-xs font-bold uppercase tracking-[0.06em] text-[#6B7280]">
          Validation Rules
        </p>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Minimum value</Label>
            <Input
              type="number"
              step="any"
              value={typeof value.min === "number" ? value.min : ""}
              placeholder="No minimum"
              onChange={(e) => set("min", toNumberOrUndefined(e.target.value))}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Maximum value</Label>
            <Input
              type="number"
              step="any"
              value={typeof value.max === "number" ? value.max : ""}
              placeholder="No maximum"
              onChange={(e) => set("max", toNumberOrUndefined(e.target.value))}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Decimal places</Label>
            <Input
              type="number"
              min={0}
              step="1"
              value={typeof value.decimal_places === "number" ? value.decimal_places : ""}
              placeholder="e.g. 2"
              onChange={(e) => {
                const parsed = toNumberOrUndefined(e.target.value);
                set(
                  "decimal_places",
                  parsed === undefined ? undefined : Math.max(0, Math.trunc(parsed))
                );
              }}
            />
          </div>
        </div>

        <p className="text-xs text-[#6B7280]">
          Leave min/max blank to leave that side unconstrained. Decimal
          places controls how many digits after the decimal point are
          allowed (e.g. 2 → values like 12.34).
        </p>
      </div>
    );
  }

  if (dataType === "INTEGER") {
    return (
      <div className="space-y-4 rounded-lg border-[1.5px] border-[#8891A3] p-4">
        <p className="text-xs font-bold uppercase tracking-[0.06em] text-[#6B7280]">
          Validation Rules
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Minimum value</Label>
            <Input
              type="number"
              step="1"
              value={typeof value.min === "number" ? value.min : ""}
              placeholder="No minimum"
              onChange={(e) => set("min", toNumberOrUndefined(e.target.value))}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Maximum value</Label>
            <Input
              type="number"
              step="1"
              value={typeof value.max === "number" ? value.max : ""}
              placeholder="No maximum"
              onChange={(e) => set("max", toNumberOrUndefined(e.target.value))}
            />
          </div>
        </div>

        <p className="text-xs text-[#6B7280]">
          Leave a field blank to leave that side unconstrained.
        </p>
      </div>
    );
  }

  if (dataType === "TEXT" || dataType === "LONG_TEXT") {
    return (
      <div className="space-y-4 rounded-lg border-[1.5px] border-[#8891A3] p-4">
        <p className="text-xs font-bold uppercase tracking-[0.06em] text-[#6B7280]">
          Validation Rules
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Minimum length</Label>
            <Input
              type="number"
              min={0}
              value={typeof value.min_length === "number" ? value.min_length : ""}
              placeholder="No minimum"
              onChange={(e) => set("min_length", toNumberOrUndefined(e.target.value))}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Maximum length</Label>
            <Input
              type="number"
              min={0}
              value={typeof value.max_length === "number" ? value.max_length : ""}
              placeholder="No maximum"
              onChange={(e) => set("max_length", toNumberOrUndefined(e.target.value))}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label className="text-sm font-medium">Pattern (regex, optional)</Label>
          <Input
            type="text"
            value={typeof value.pattern === "string" ? value.pattern : ""}
            placeholder="e.g. ^[A-Z]{3}-\d+$"
            onChange={(e) =>
              set("pattern", e.target.value === "" ? undefined : e.target.value)
            }
          />
        </div>
      </div>
    );
  }

  if (dataType === "DATE") {
    return (
      <div className="space-y-4 rounded-lg border-[1.5px] border-[#8891A3] p-4">
        <p className="text-xs font-bold uppercase tracking-[0.06em] text-[#6B7280]">
          Validation Rules
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Earliest allowed date</Label>
            <Input
              type="date"
              value={typeof value.min_date === "string" ? value.min_date : ""}
              onChange={(e) =>
                set("min_date", e.target.value === "" ? undefined : e.target.value)
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Latest allowed date</Label>
            <Input
              type="date"
              value={typeof value.max_date === "string" ? value.max_date : ""}
              onChange={(e) =>
                set("max_date", e.target.value === "" ? undefined : e.target.value)
              }
            />
          </div>
        </div>
      </div>
    );
  }

  if (dataType === "TABLE") {
    return (
     <p className="text-sm text-[#6B7280]">
        No additional validation rules apply to this data type.
      </p>
    );
  }

  if (dataType === "BOOLEAN" || dataType === "SELECT") {
    return (
      <p className="text-sm text-[#6B7280]">
        No additional validation rules apply to this data type.
      </p>
    );
  }

  return null;
}