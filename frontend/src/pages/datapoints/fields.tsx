import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { memo, useMemo, useState, type ChangeEvent, type FocusEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell as UiTableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import type {
  DatapointDetail,
  DatapointTableColumn,
  Unit,
} from "@/types/datapoint";

import {
  validateValue,
  validateRowCount,
  type CellPrimitive,
} from "@/pages/datapoints/TableDatapointvalidation";
import {
  emptyTableCell,
  fixedRowDraft,
  type TableAnswerDraft,
  type TableCellDraft,
  type TableRowDraft,
} from "@/pages/datapoints/tableAnswerAdapter";

/* =========================================================
   FIELD VALUE
========================================================= */

export type FieldValue =
  | string
  | number
  | boolean
  | TableAnswerDraft
  | null
  | undefined;

/* =========================================================
   SHARED FIELD PROPS
   ---------------------------------------------------------
   required / error / readOnly are all optional overrides:
   - required defaults to datapoint.is_required if omitted
   - error, when present, renders a message and switches the
     field into an error visual state
   - readOnly keeps the value visible/selectable but blocks
     editing (distinct from `disabled`, which also mutes the
     visual style)
========================================================= */

interface FieldProps {
  datapoint: DatapointDetail;
  value?: FieldValue;
  onChange?: (value: FieldValue) => void;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  error?: string | null;
  /** Resolved Unit objects keyed by Unit ID. Optional — omitted
   *  callers see no unit suffix, same as before this change. */
  unitsById?: Record<string, Unit>;
}

/* =========================================================
   TABLE VALUE
========================================================= */

type TableRowValue = TableRowDraft;

// Stable reference so a missing/invalid table value never
// forces downstream useMemo hooks to see a "new" array on
// every render (see TableField below).
const EMPTY_TABLE_VALUE: TableRowValue[] = [];

// Sentinel used only inside the SELECT field's Radix <Select>,
// since Radix items can't have an empty-string value. Mapped
// back to null the moment it leaves this component.
const SELECT_CLEAR_VALUE = "__clear__";

/* =========================================================
   UNIT LOOKUP
   ---------------------------------------------------------
   default_unit — on BOTH Datapoint and DatapointTableColumn —
   may arrive from the backend either as a bare unit ID string
   or as a nested Unit object (id + code + ...). Every caller
   that reads a default_unit MUST go through one of these two
   helpers rather than assuming one shape, since assuming
   "always a string ID" is exactly what silently dropped the
   unit suffix on both scalar fields and table cells before
   this fix — resolveUnitCode(someUnitObject, unitsById) tried
   to look the object up as a map key and always got undefined.

   resolveUnitId   -> the ID, for building a write payload.
   resolveUnitCode -> the display code, for rendering. Uses the
                      object's own `code` directly when the
                      backend already nested it, so display
                      doesn't even depend on unitsById having
                      loaded; falls back to the unitsById map
                      lookup when only a bare ID is available.
========================================================= */

function resolveUnitId(
  unit: string | Unit | null | undefined
): string | null {
  if (!unit) return null;
  return typeof unit === "string" ? unit : unit.id ?? null;
}

function resolveUnitCode(
  unit: string | Unit | null | undefined,
  unitsById?: Record<string, Unit>
): string | null {
  if (!unit) return null;

  if (typeof unit === "object") {
    return unit.code ?? null;
  }

  return unitsById?.[unit]?.code ?? null;
}

/* Narrows a FieldValue (or unknown table-cell value) down to
   the CellPrimitive shape validateValue expects. */
function toCellPrimitive(value: unknown): CellPrimitive {
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  return null;
}

/* =========================================================
   SHARED STYLE HELPERS
   ---------------------------------------------------------
   These are passed as `className` into shadcn's Input /
   Textarea / Select / Checkbox — shadcn's own `cn()` merge
   (clsx + tailwind-merge) means these override the
   component's default border/ring colors without fighting
   its base layout classes.
========================================================= */

const normalBorderClasses =
  "border-[#8891A3] focus-visible:border-[#4A3FD6] focus-visible:ring-4 focus-visible:ring-[#ECE9FB]";

const errorBorderClasses =
  "border-[#B3403B] focus-visible:border-[#B3403B] focus-visible:ring-4 focus-visible:ring-[#FBEAEA]";

const readOnlyClasses = "cursor-default bg-[#F7F7FB] text-[#4B4E5E]";

function getFieldClassName({
  hasError,
  readOnly,
  cell = false,
}: {
  hasError: boolean;
  readOnly?: boolean;
  cell?: boolean;
}): string {
  return cn(
    cell ? "h-9 min-w-[140px]" : "h-10",
    "text-[#22243A]",
    hasError ? errorBorderClasses : normalBorderClasses,
    readOnly && readOnlyClasses
  );
}

/* =========================================================
   SHARED FIELD WRAPPER
   ---------------------------------------------------------
   - required: falls back to datapoint.is_required unless
     explicitly overridden
   - error: renders below the field, replacing the
     description while present
========================================================= */

function FieldWrapper({
  datapoint,
  required,
  error,
  children,
}: {
  datapoint: DatapointDetail;
  required?: boolean;
  error?: string | null;
  children: ReactNode;
}) {
  const isRequired = required ?? datapoint.is_required;

  return (
    <div className="space-y-2">
      <label className="text-sm font-bold text-[#22243A]">
        {datapoint.label}

        {isRequired && (
          <span className="ml-1 text-[#B3403B]" aria-hidden="true">
            *
          </span>
        )}
      </label>

      {children}

      {error ? (
        <p className="text-xs font-medium leading-5 text-[#B3403B]">{error}</p>
      ) : (
        datapoint.description && (
          <p className="text-xs leading-5 text-[#6B7280]">
            {datapoint.description}
          </p>
        )
      )}
    </div>
  );
}

/* =========================================================
   SHARED NUMERIC INPUT
   ---------------------------------------------------------
   A plain controlled <input type="number"> whose `value` is
   the *parsed* number breaks mid-typing — e.g. typing "1."
   collapses to "1" because Number("1.") === 1, and typing
   just "-" becomes NaN.

   Fix: keep a local "draft" string while focused, and only
   report the parsed value upward (via onCommit) on blur.
   While not focused, the input shows the real committed
   value, so external resets (e.g. form.reset()) still work.

   Built on shadcn's <Input> rather than a raw <input>.
========================================================= */

function NumericInput({
  value,
  kind,
  disabled,
  readOnly,
  hasError,
  onCommit,
  cell = false,
}: {
  value: unknown;
  kind: "INTEGER" | "DECIMAL";
  disabled?: boolean;
  readOnly?: boolean;
  hasError: boolean;
  onCommit: (rawValue: string) => void;
  cell?: boolean;
}) {
  const committedValue =
    typeof value === "number" || typeof value === "string" ? String(value) : "";

  const [draft, setDraft] = useState(committedValue);
  const [editing, setEditing] = useState(false);

  const displayValue = editing ? draft : committedValue;
  const isInteractive = !disabled && !readOnly;

  return (
    <Input
      type="number"
      step={kind === "DECIMAL" ? "any" : "1"}
      value={displayValue}
      disabled={disabled}
      readOnly={readOnly}
      aria-invalid={hasError || undefined}
      onFocus={() => {
        if (!isInteractive) return;
        setDraft(committedValue);
        setEditing(true);
      }}
      onChange={(event) => {
        if (!isInteractive) return;
        setDraft(event.target.value);
      }}
      onBlur={(event) => {
        if (!isInteractive) return;
        setEditing(false);
        onCommit(event.target.value);
      }}
      className={getFieldClassName({ hasError, readOnly, cell })}
    />
  );
}

function parseNumeric(kind: "INTEGER" | "DECIMAL", rawValue: string): number | null {
  if (rawValue === "" || rawValue === "-") return null;

  const parsed = kind === "INTEGER" ? Number.parseInt(rawValue, 10) : Number(rawValue);

  return Number.isNaN(parsed) ? null : parsed;
}

/* =========================================================
   DECIMAL
========================================================= */

export function DecimalField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
  unitsById,
}: FieldProps) {
  const isRequired = required ?? datapoint.is_required;
  const resolvedError =
    error ??
    validateValue(
      "DECIMAL",
      datapoint.validation_metadata,
      toCellPrimitive(value),
      isRequired
    );
  const unitCode = resolveUnitCode(datapoint.default_unit, unitsById);

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <div className="flex items-center gap-2">
        <NumericInput
          kind="DECIMAL"
          value={value}
          disabled={disabled}
          readOnly={readOnly}
          hasError={Boolean(resolvedError)}
          onCommit={(rawValue) => onChange?.(parseNumeric("DECIMAL", rawValue))}
        />
        {unitCode && (
          <span className="shrink-0 text-sm text-[#6B7280]">{unitCode}</span>
        )}
      </div>
    </FieldWrapper>
  );
}

/* =========================================================
   INTEGER
========================================================= */

export function IntegerField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
  unitsById,
}: FieldProps) {
  const isRequired = required ?? datapoint.is_required;
  const resolvedError =
    error ??
    validateValue(
      "INTEGER",
      datapoint.validation_metadata,
      toCellPrimitive(value),
      isRequired
    );
  const unitCode = resolveUnitCode(datapoint.default_unit, unitsById);

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <div className="flex items-center gap-2">
        <NumericInput
          kind="INTEGER"
          value={value}
          disabled={disabled}
          readOnly={readOnly}
          hasError={Boolean(resolvedError)}
          onCommit={(rawValue) => onChange?.(parseNumeric("INTEGER", rawValue))}
        />
        {unitCode && (
          <span className="shrink-0 text-sm text-[#6B7280]">{unitCode}</span>
        )}
      </div>
    </FieldWrapper>
  );
}

/* =========================================================
   TEXT
========================================================= */

export function TextField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
}: FieldProps) {
  const isRequired = required ?? datapoint.is_required;
  const resolvedError =
    error ??
    validateValue(
      "TEXT",
      datapoint.validation_metadata,
      toCellPrimitive(value),
      isRequired
    );

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <Input
        type="text"
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={Boolean(resolvedError) || undefined}
        onChange={(event) => onChange?.(event.target.value)}
        className={getFieldClassName({ hasError: Boolean(resolvedError), readOnly })}
      />
    </FieldWrapper>
  );
}

/* =========================================================
   LONG TEXT
========================================================= */

export function LongTextField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
}: FieldProps) {
  const isRequired = required ?? datapoint.is_required;
  const resolvedError =
    error ??
    validateValue(
      "LONG_TEXT",
      datapoint.validation_metadata,
      toCellPrimitive(value),
      isRequired
    );

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <Textarea
        rows={5}
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={Boolean(resolvedError) || undefined}
        onChange={(event) => onChange?.(event.target.value)}
        className={cn(
          "min-h-[120px] resize-y text-[#22243A]",
          resolvedError ? errorBorderClasses : normalBorderClasses,
          readOnly && readOnlyClasses
        )}
      />
    </FieldWrapper>
  );
}

/* =========================================================
   BOOLEAN
   ---------------------------------------------------------
   Radix's Checkbox has no true "readOnly" semantics either,
   so readOnly is emulated the same way as before: onChange
   is intercepted and ignored while non-interactive, and the
   wrapper gets a distinct (non-greyed) readOnly style rather
   than a hard `disabled` look.
========================================================= */

export function BooleanField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
}: FieldProps) {
  const checked = value === true;
  const isInteractive = !disabled && !readOnly;

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <label
        className={cn(
          "flex min-h-10 items-center gap-3 rounded-lg border-[1.5px] bg-white px-3 text-sm text-[#22243A] has-[[data-state]:focus-visible]:ring-4 has-[[data-state]:focus-visible]:ring-offset-1",
          error
            ? "border-[#B3403B] has-[[data-state]:focus-visible]:ring-[#FBEAEA]"
            : "border-[#8891A3] has-[[data-state]:focus-visible]:ring-[#ECE9FB]",
          readOnly && readOnlyClasses,
          isInteractive ? "cursor-pointer" : "cursor-not-allowed opacity-50"
        )}
      >
        <Checkbox
          checked={checked}
          disabled={disabled}
          aria-readonly={readOnly || undefined}
          aria-invalid={Boolean(error) || undefined}
          onCheckedChange={(next) => {
            if (!isInteractive) return;
            onChange?.(next === true);
          }}
        />

        <span>{checked ? "Yes" : "No"}</span>
      </label>
    </FieldWrapper>
  );
}

/* =========================================================
   SELECT
   ---------------------------------------------------------
   Backend: DatapointOption has code, label, display_order,
   is_active. Built on shadcn's <Select> instead of a native
   <select>. Radix Select items can't carry an empty-string
   value, so a SELECT_CLEAR_VALUE sentinel stands in for "no
   option chosen" and is translated back to null on the way
   out — the same pattern already used for unit_family /
   default_unit elsewhere in this codebase.
========================================================= */

export function SelectField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
}: FieldProps) {
  const options = useMemo(
    () =>
      [...(datapoint.options ?? [])]
        .filter((option) => option.is_active)
        .sort((a, b) => a.display_order - b.display_order),
    [datapoint.options]
  );

  const selectValue = typeof value === "string" && value !== "" ? value : SELECT_CLEAR_VALUE;

  const isRequired = required ?? datapoint.is_required;
  const resolvedError =
    error ??
    validateValue(
      "SELECT",
      datapoint.validation_metadata,
      toCellPrimitive(value),
      isRequired
    );

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <Select
        value={selectValue}
        disabled={disabled || readOnly}
        onValueChange={(next) => {
          onChange?.(next === SELECT_CLEAR_VALUE ? null : next);
        }}
      >
        <SelectTrigger
          aria-invalid={Boolean(resolvedError) || undefined}
          className={cn("w-full", getFieldClassName({ hasError: Boolean(resolvedError), readOnly }))}
        >
          <SelectValue placeholder="Select an option" />
        </SelectTrigger>

        <SelectContent>
          <SelectItem value={SELECT_CLEAR_VALUE}>Select an option</SelectItem>

          {options.map((option) => (
            <SelectItem key={option.id} value={option.id}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldWrapper>
  );
}

/* =========================================================
   DATE
========================================================= */

export function DateField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
}: FieldProps) {
  const isRequired = required ?? datapoint.is_required;
  const resolvedError =
    error ??
    validateValue(
      "DATE",
      datapoint.validation_metadata,
      toCellPrimitive(value),
      isRequired
    );

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <Input
        type="date"
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={Boolean(resolvedError) || undefined}
        onChange={(event) => {
          if (readOnly) return;
          onChange?.(event.target.value === "" ? null : event.target.value);
        }}
        className={getFieldClassName({ hasError: Boolean(resolvedError), readOnly })}
      />
    </FieldWrapper>
  );
}
/* =========================================================
   TABLE
   ---------------------------------------------------------
   Value structure (generic, M5-ready):

     TableRowValue = {
       id: string              // stable client key; for fixed
                                // rows this is `fixed:${row.code}`,
                                // for dynamic rows a generated id
       row_code: string | null // matches DatapointTableRow.code
                                // for fixed rows; null for rows
                                // added dynamically (no fixed
                                // definition exists for them)
       is_dynamic: boolean
       [columnCode]: unknown   // one key per column, keyed by
                                // DatapointTableColumn.code
     }

   This is intentionally flat rather than a nested
   { row, cells: [...] } shape, but every piece of information
   an AnswerTableRow/AnswerTableCell pair needs is already
   present and separable: `id`/`row_code`/`is_dynamic` map onto
   AnswerTableRow fields, and the remaining column-code keys map
   onto one AnswerTableCell each. M5 can serialize this directly
   without changing what this component reads or writes.

   SELECT COLUMN CONTRACT GAP:
   DatapointTableColumn (types/datapoint.ts) has no `options`
   field — unlike the top-level Datapoint, which gets its
   choices from a separate DatapointOption list. There is
   currently no API-provided source of selectable values for a
   SELECT-typed table column, so it cannot be rendered as a
   working dropdown without inventing values that don't exist
   on the backend. It renders as a disabled, clearly-labeled
   placeholder instead. Once the backend exposes column-level
   options (e.g. a `DatapointTableColumn.options` field, or a
   sibling table mirroring DatapointOption), swap the SELECT
   branch in DataCell for a real <Select>.
========================================================= */

let dynamicRowCounter = 0;

function generateRowId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  dynamicRowCounter += 1;
  return `dynamic-${Date.now()}-${dynamicRowCounter}`;
}

function cellPrimitive(cell: TableCellDraft | undefined): CellPrimitive {
  if (!cell) return null;
  return (
    cell.decimal_value ??
    cell.integer_value ??
    cell.text_value ??
    cell.boolean_value ??
    cell.date_value ??
    null
  );
}

function typedCellValue(
  column: DatapointTableColumn,
  rawValue: unknown,
  current?: TableCellDraft,
): TableCellDraft {
  const base = { ...emptyTableCell(column), ...current, column: column.id };

  switch (column.data_type) {
    case "INTEGER":
      return {
        ...base,
        integer_value: parseNumeric("INTEGER", String(rawValue ?? "")) as number | null,
        // Fall back to the column's default unit only if this cell has
        // never had a unit set (i.e. first-time entry, not a hydrated
        // saved cell whose unit — including an intentional null — should
        // never be overwritten here). Always go through resolveUnitId so
        // this stores a plain unit-ID string even if column.default_unit
        // turns out to be a nested Unit object at runtime — the write
        // payload must never carry a whole object here.
        unit: current?.unit ?? resolveUnitId(column.default_unit) ?? null,
      };
    case "DECIMAL":
      return {
        ...base,
        decimal_value: parseNumeric("DECIMAL", String(rawValue ?? "")) as number | null,
        unit: current?.unit ?? resolveUnitId(column.default_unit) ?? null,
      };
    case "BOOLEAN":
      return { ...base, boolean_value: rawValue === true };
    case "DATE":
      return { ...base, date_value: rawValue === "" || rawValue == null ? null : String(rawValue) };
    case "TEXT":
    case "LONG_TEXT":
      return { ...base, text_value: rawValue === "" || rawValue == null ? null : String(rawValue) };
    default:
      return base;
  }
}
/* ---- text cell (single-line or multiline), draft+commit-on-blur ---- */

function TextCellInput({
  value,
  disabled,
  readOnly,
  multiline = false,
  onCommit,
}: {
  value: unknown;
  disabled?: boolean;
  readOnly?: boolean;
  multiline?: boolean;
  onCommit: (rawValue: string) => void;
}) {
  const committedValue = typeof value === "string" ? value : "";
  const [draft, setDraft] = useState(committedValue);
  const [editing, setEditing] = useState(false);
  const displayValue = editing ? draft : committedValue;
  const isInteractive = !disabled && !readOnly;

  const handleFocus = () => {
    if (!isInteractive) return;
    setDraft(committedValue);
    setEditing(true);
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (!isInteractive) return;
    setDraft(event.target.value);
  };

  const handleBlur = (event: FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (!isInteractive) return;
    setEditing(false);
    onCommit(event.target.value);
  };

  if (multiline) {
    return (
      <Textarea
        rows={2}
        value={displayValue}
        disabled={disabled}
        readOnly={readOnly}
        onFocus={handleFocus}
        onChange={handleChange}
        onBlur={handleBlur}
        className="min-w-[160px] resize-y border-[#8891A3] text-[#22243A]"
      />
    );
  }

  return (
    <Input
      type="text"
      value={displayValue}
      disabled={disabled}
      readOnly={readOnly}
      onFocus={handleFocus}
      onChange={handleChange}
      onBlur={handleBlur}
      className={getFieldClassName({ hasError: false, readOnly, cell: true })}
    />
  );
}

/* ---- dispatches to the right control per column.data_type ---- */

const DataCell = memo(function DataCell({
  rowKey,
  column,
  value,
  disabled,
  readOnly,
  unitsById,
  onCommit,
}: {
  rowKey: string;
  column: DatapointTableColumn;
  value: unknown;
  disabled?: boolean;
  readOnly?: boolean;
  unitsById?: Record<string, Unit>;
  onCommit: (rowKey: string, columnId: string, rawValue: unknown) => void;
}) {
  const isInteractive = !disabled && !readOnly;

  const cellError = validateValue(
    column.data_type,
    column.validation_metadata ?? {},
    toCellPrimitive(value),
    column.is_required
  );

  switch (column.data_type) {
    case "INTEGER":
    case "DECIMAL": {
      const unitCode = resolveUnitCode(column.default_unit, unitsById);
      return (
        <div>
          <div className="flex items-center gap-2">
            <NumericInput
              kind={column.data_type}
              value={value}
              disabled={disabled}
              readOnly={readOnly}
              hasError={Boolean(cellError)}
              cell
              onCommit={(rawValue) => onCommit(rowKey, column.id, rawValue)}
            />
            {unitCode && (
              <span className="shrink-0 text-sm text-[#6B7280]">{unitCode}</span>
            )}
          </div>
          {cellError && <p className="mt-1 text-xs text-[#B3403B]">{cellError}</p>}
        </div>
      );
    }

    case "BOOLEAN":
      return (
        <div className="flex h-9 min-w-[100px] items-center">
          <Checkbox
            checked={value === true}
            disabled={disabled}
            aria-readonly={readOnly || undefined}
            onCheckedChange={(next) => {
              if (!isInteractive) return;
              onCommit(rowKey, column.id, next === true);
            }}
          />
        </div>
      );

        case "DATE":
      return (
        <div>
          <Input
            type="date"
            value={typeof value === "string" ? value : ""}
            disabled={disabled}
            readOnly={readOnly}
            onChange={(event) => {
              if (!isInteractive) return;
              onCommit(rowKey, column.id, event.target.value);
            }}
            className={getFieldClassName({ hasError: Boolean(cellError), readOnly, cell: true })}
          />
          {cellError && <p className="mt-1 text-xs text-[#B3403B]">{cellError}</p>}
        </div>
      );

    case "LONG_TEXT":
      return (
        <div>
          <TextCellInput
            multiline
            value={value}
            disabled={disabled}
            readOnly={readOnly}
          onCommit={(rawValue) => onCommit(rowKey, column.id, rawValue)}
          />
          {cellError && <p className="mt-1 text-xs text-[#B3403B]">{cellError}</p>}
        </div>
      );

    case "TEXT":
      return (
        <div>
          <TextCellInput
            value={value}
            disabled={disabled}
            readOnly={readOnly}
          onCommit={(rawValue) => onCommit(rowKey, column.id, rawValue)}
          />
          {cellError && <p className="mt-1 text-xs text-[#B3403B]">{cellError}</p>}
        </div>
      );

    case "SELECT":
      // Contract gap — see file header comment. Rendered as an
      // explicitly disabled field rather than a fake dropdown.
      return (
        <Input
          type="text"
          value=""
          disabled
          readOnly
          placeholder="Not available — column has no option data"
          className={getFieldClassName({ hasError: false, readOnly: true, cell: true })}
        />
      );

    case "TABLE":
      // Nested tables are unsupported by design.
      return (
        <Input
          type="text"
          value=""
          disabled
          readOnly
          placeholder="Nested tables unsupported"
          className={getFieldClassName({ hasError: false, readOnly: true, cell: true })}
        />
      );

    default:
      return null;
  }
});

const TableRowItem = memo(function TableRowItem({
  rowLabel,
  rowKey,
  isDynamic,
  columns,
  rowValue,
  disabled,
  readOnly,
  unitsById,
  onCommit,
  onLabelChange,
  onRemove,
  showActionsColumn,
}: {
  rowLabel: string;
  rowKey: string;
  isDynamic: boolean;
  columns: DatapointTableColumn[];
  rowValue: TableRowValue | undefined;
  disabled?: boolean;
  readOnly?: boolean;
  unitsById?: Record<string, Unit>;
  onCommit: (rowKey: string, columnId: string, rawValue: unknown) => void;
  onLabelChange?: (label: string) => void;
  onRemove?: () => void;
  showActionsColumn: boolean;
}) {
  return (
    <TableRow>
      <UiTableCell className="font-semibold text-[#22243A]">
        {isDynamic && onLabelChange ? (
          <Input
            value={rowLabel}
            onChange={(event) => onLabelChange(event.target.value)}
            aria-label="Dynamic row label"
            className="min-w-[160px]"
          />
        ) : (
          rowLabel
        )}
      </UiTableCell>

      {columns.map((column) => (
        <UiTableCell key={column.id}>
          <DataCell
            rowKey={rowKey}
            column={column}
            value={cellPrimitive(rowValue?.cells.find((cell) => cell.column === column.id))}
            disabled={disabled}
            readOnly={readOnly}
            unitsById={unitsById}
            onCommit={onCommit}
          />
        </UiTableCell>
      ))}

      {showActionsColumn && (
        <UiTableCell className="text-right">
          {onRemove && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onRemove}
              aria-label="Remove row"
            >
              <Trash2 className="h-4 w-4 text-red-600" />
            </Button>
          )}
        </UiTableCell>
      )}
    </TableRow>
  );
});

export function TableField({
  datapoint,
  value,
  onChange,
  disabled,
  readOnly,
  required,
  error,
  unitsById,
}: FieldProps) {
  const columns = useMemo(
    () => [...(datapoint.table_columns ?? [])].sort((a, b) => a.display_order - b.display_order),
    [datapoint.table_columns]
  );

  const rows = useMemo(
    () => [...(datapoint.table_rows ?? [])].sort((a, b) => a.display_order - b.display_order),
    [datapoint.table_rows]
  );

  const tableValue = useMemo<TableRowValue[]>(
    () => (Array.isArray(value) ? value : EMPTY_TABLE_VALUE),
    [value]
  );

  const valueByDefinitionRow = useMemo(() => {
    const map = new Map<string, TableRowValue>();
    for (const row of tableValue) {
      if (row.definition_row) {
        map.set(row.definition_row, row);
      }
    }
    return map;
  }, [tableValue]);

  const dynamicRows = useMemo(
    () => tableValue.filter((row) => row.definition_row === null),
    [tableValue]
  );

  const columnById = useMemo(() => {
    const map = new Map<string, DatapointTableColumn>();
    for (const column of columns) map.set(column.id, column);
    return map;
  }, [columns]);

  const allowDynamicRows = Boolean(datapoint.allow_dynamic_rows);
  const canEdit = !disabled && !readOnly;

  const rowCountError = allowDynamicRows
    ? validateRowCount(tableValue.length, datapoint.validation_metadata)
    : null;
  const resolvedError = error ?? rowCountError;

  const commitCell = (
    rowKey: string,
    columnId: string,
    rawValue: unknown
  ) => {
    const column = columnById.get(columnId);
    if (!column) return;
    const existingRows = tableValue.some((row) => row.id === rowKey)
      ? tableValue
      : (() => {
          const definition = rows.find((row) => row.id === rowKey);
          return definition ? [...tableValue, fixedRowDraft(definition)] : tableValue;
        })();
    const nextRows = existingRows.map((row) => {
      if (row.id !== rowKey) return row;
      const existing = row.cells.find((cell) => cell.column === columnId);
      const nextCell = typedCellValue(column, rawValue, existing);
      return {
        ...row,
        cells: [...row.cells.filter((cell) => cell.column !== columnId), nextCell],
      };
    });
    onChange?.(nextRows);
  };

  const addDynamicRow = () => {
    const newRow: TableRowValue = {
      id: generateRowId(),
      definition_row: null,
      label: `Row ${dynamicRows.length + 1}`,
      display_order: Math.max(-1, ...tableValue.map((row) => row.display_order)) + 1,
      cells: [],
    };
    onChange?.([...tableValue, newRow]);
  };

  const removeDynamicRow = (id: string) => {
    onChange?.(tableValue.filter((row) => row.id !== id));
  };

  const updateDynamicLabel = (id: string, label: string) => {
    onChange?.(tableValue.map((row) => (row.id === id ? { ...row, label } : row)));
  };

  const showActionsColumn = allowDynamicRows;
  const totalColSpan = Math.max(columns.length + 1 + (showActionsColumn ? 1 : 0), 1);

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={resolvedError}>
      <div
        className={cn(
          "overflow-hidden rounded-lg border-[1.5px]",
          resolvedError ? "border-[#B3403B]" : "border-[#8891A3]"
        )}
      >
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-[#F5F5FB] hover:bg-[#F5F5FB]">
                <TableHead className="text-[10.5px] font-bold uppercase tracking-[0.06em] text-[#6B7280]">
                  {datapoint.label}
                </TableHead>

                {columns.map((column) => (
                  <TableHead
                    key={column.id}
                    className="text-[10.5px] font-bold uppercase tracking-[0.06em] text-[#6B7280]"
                  >
                    {column.label}
                    {column.is_required && <span className="ml-1 text-[#B3403B]">*</span>}
                  </TableHead>
                ))}

                {showActionsColumn && (
                  <TableHead className="w-16 text-right text-[10.5px] font-bold uppercase tracking-[0.06em] text-[#6B7280]">
                    Actions
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>

            <TableBody>
              {rows.map((row) => (
                <TableRowItem
                  key={row.id}
                  rowLabel={row.label}
                  rowKey={(valueByDefinitionRow.get(row.id) ?? fixedRowDraft(row)).id}
                  isDynamic={false}
                  columns={columns}
                  rowValue={valueByDefinitionRow.get(row.id) ?? fixedRowDraft(row)}
                  disabled={disabled}
                  readOnly={readOnly}
                  unitsById={unitsById}
                  onCommit={commitCell}
                  showActionsColumn={showActionsColumn}
                />
              ))}

              {dynamicRows.map((rowValue, index) => (
                <TableRowItem
                  key={String(rowValue.id)}
                  rowLabel={rowValue.label || `Row ${index + 1}`}
                  rowKey={String(rowValue.id)}
                  isDynamic
                  columns={columns}
                  rowValue={rowValue}
                  disabled={disabled}
                  readOnly={readOnly}
                  unitsById={unitsById}
                  onCommit={commitCell}
                  onLabelChange={canEdit ? (label) => updateDynamicLabel(String(rowValue.id), label) : undefined}
                  onRemove={canEdit ? () => removeDynamicRow(String(rowValue.id)) : undefined}
                  showActionsColumn={showActionsColumn}
                />
              ))}

              {rows.length === 0 && dynamicRows.length === 0 && (
                <TableRow>
                  <UiTableCell colSpan={totalColSpan} className="py-8 text-center text-sm text-[#6B7280]">
                    {allowDynamicRows ? "No rows added yet." : "No fixed rows defined."}
                  </UiTableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {allowDynamicRows && canEdit && (
          <div className="flex justify-end border-t border-[#8891A3] bg-[#FAFAFC] px-3 py-2">
            <Button type="button" variant="outline" size="sm" onClick={addDynamicRow}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Add Row
            </Button>
          </div>
        )}
      </div>
    </FieldWrapper>
  );
}