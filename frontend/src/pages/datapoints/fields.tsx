import { memo, useMemo, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
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
} from "@/types/datapoint";

/* =========================================================
   FIELD VALUE
========================================================= */

export type FieldValue =
  | string
  | number
  | boolean
  | Record<string, unknown>[]
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
}

/* =========================================================
   TABLE VALUE
========================================================= */

type TableRowValue = Record<string, unknown>;

// Stable reference so a missing/invalid table value never
// forces downstream useMemo hooks to see a "new" array on
// every render (see TableField below).
const EMPTY_TABLE_VALUE: TableRowValue[] = [];

// Sentinel used only inside the SELECT field's Radix <Select>,
// since Radix items can't have an empty-string value. Mapped
// back to null the moment it leaves this component.
const SELECT_CLEAR_VALUE = "__clear__";

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
}: FieldProps) {
  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <NumericInput
        kind="DECIMAL"
        value={value}
        disabled={disabled}
        readOnly={readOnly}
        hasError={Boolean(error)}
        onCommit={(rawValue) => onChange?.(parseNumeric("DECIMAL", rawValue))}
      />
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
}: FieldProps) {
  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <NumericInput
        kind="INTEGER"
        value={value}
        disabled={disabled}
        readOnly={readOnly}
        hasError={Boolean(error)}
        onCommit={(rawValue) => onChange?.(parseNumeric("INTEGER", rawValue))}
      />
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
  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <Input
        type="text"
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={Boolean(error) || undefined}
        onChange={(event) => onChange?.(event.target.value)}
        className={getFieldClassName({ hasError: Boolean(error), readOnly })}
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
  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <Textarea
        rows={5}
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={Boolean(error) || undefined}
        onChange={(event) => onChange?.(event.target.value)}
        className={cn(
          "min-h-[120px] resize-y text-[#22243A]",
          error ? errorBorderClasses : normalBorderClasses,
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

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <Select
        value={selectValue}
        disabled={disabled || readOnly}
        onValueChange={(next) => {
          onChange?.(next === SELECT_CLEAR_VALUE ? null : next);
        }}
      >
        <SelectTrigger
          aria-invalid={Boolean(error) || undefined}
          className={cn("w-full", getFieldClassName({ hasError: Boolean(error), readOnly }))}
        >
          <SelectValue placeholder="Select an option" />
        </SelectTrigger>

        <SelectContent>
          <SelectItem value={SELECT_CLEAR_VALUE}>Select an option</SelectItem>

          {options.map((option) => (
            <SelectItem key={option.id} value={option.code}>
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
  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <Input
        type="date"
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={Boolean(error) || undefined}
        onChange={(event) => {
          if (readOnly) return;
          onChange?.(event.target.value === "" ? null : event.target.value);
        }}
        className={getFieldClassName({ hasError: Boolean(error), readOnly })}
      />
    </FieldWrapper>
  );
}

/* =========================================================
   TABLE
   ---------------------------------------------------------
   Performance notes for large dynamic tables:
   - columns/rows sorted once via useMemo, not every render
   - tableValue itself is memoized against a stable empty-
     array constant so it never appears "new" when `value`
     isn't an array — this is what was breaking
     valueByRowCode's memoization before
   - cell lookup uses a Map (O(1)) instead of Array.find (O(n))
   - each row is React.memo'd so editing one row's cell does
     not re-render every other row
   - each cell buffers its own draft and only commits (and
     only triggers a parent re-render) on blur

   Built on shadcn's Table/TableHeader/TableBody/TableRow/
   TableHead/TableCell instead of raw <table> markup.
========================================================= */

const DataCell = memo(function DataCell({
  rowCode,
  column,
  value,
  disabled,
  readOnly,
  onCommit,
}: {
  rowCode: string;
  column: DatapointTableColumn;
  value: unknown;
  disabled?: boolean;
  readOnly?: boolean;
  onCommit: (rowCode: string, columnCode: string, rawValue: string) => void;
}) {
  // All hooks are called unconditionally, every render —
  // `isNumeric` only affects which JSX attributes are used
  // below, never whether a hook runs.
  const isNumeric = column.data_type === "INTEGER" || column.data_type === "DECIMAL";
  const isInteractive = !disabled && !readOnly;

  const committedValue =
    typeof value === "string" || typeof value === "number" ? String(value) : "";

  const [draft, setDraft] = useState(committedValue);
  const [editing, setEditing] = useState(false);

  const displayValue = editing ? draft : committedValue;

  return (
    <Input
      type={isNumeric ? "number" : "text"}
      step={column.data_type === "DECIMAL" ? "any" : "1"}
      value={displayValue}
      disabled={disabled}
      readOnly={readOnly}
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
        onCommit(rowCode, column.code, event.target.value);
      }}
      className={getFieldClassName({ hasError: false, readOnly, cell: true })}
    />
  );
});

const TableRowItem = memo(function TableRowItem({
  rowLabel,
  rowCode,
  columns,
  rowValue,
  disabled,
  readOnly,
  onCommit,
}: {
  rowLabel: string;
  rowCode: string;
  columns: DatapointTableColumn[];
  rowValue: TableRowValue | undefined;
  disabled?: boolean;
  readOnly?: boolean;
  onCommit: (rowCode: string, columnCode: string, rawValue: string) => void;
}) {
  return (
    <TableRow>
      <UiTableCell className="font-semibold text-[#22243A]">{rowLabel}</UiTableCell>

      {columns.map((column) => (
        <UiTableCell key={column.id}>
          <DataCell
            rowCode={rowCode}
            column={column}
            value={rowValue?.[column.code]}
            disabled={disabled}
            readOnly={readOnly}
            onCommit={onCommit}
          />
        </UiTableCell>
      ))}
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
}: FieldProps) {
  const columns = useMemo(
    () =>
      [...(datapoint.table_columns ?? [])].sort(
        (a, b) => a.display_order - b.display_order
      ),
    [datapoint.table_columns]
  );

  const rows = useMemo(
    () =>
      [...(datapoint.table_rows ?? [])].sort(
        (a, b) => a.display_order - b.display_order
      ),
    [datapoint.table_rows]
  );

  // Fixed: previously `Array.isArray(value) ? value : []` built
  // a brand-new [] literal on every render whenever value wasn't
  // an array, which made valueByRowCode's useMemo below think its
  // dependency changed every render. Falling back to a stable,
  // module-level EMPTY_TABLE_VALUE constant (and memoizing on
  // `value` itself) fixes that.
  const tableValue = useMemo<TableRowValue[]>(
    () => (Array.isArray(value) ? value : EMPTY_TABLE_VALUE),
    [value]
  );

  const valueByRowCode = useMemo(() => {
    const map = new Map<string, TableRowValue>();
    for (const row of tableValue) {
      if (typeof row.row_code === "string") {
        map.set(row.row_code, row);
      }
    }
    return map;
  }, [tableValue]);

  const columnByCode = useMemo(() => {
    const map = new Map<string, DatapointTableColumn>();
    for (const column of columns) map.set(column.code, column);
    return map;
  }, [columns]);

  const commitCell = (rowCode: string, columnCode: string, rawValue: string) => {
    const column = columnByCode.get(columnCode);

    let parsed: unknown;
    if (column?.data_type === "INTEGER") {
      parsed = parseNumeric("INTEGER", rawValue);
    } else if (column?.data_type === "DECIMAL") {
      parsed = parseNumeric("DECIMAL", rawValue);
    } else {
      parsed = rawValue === "" ? null : rawValue;
    }

    const existing = valueByRowCode.get(rowCode);
    const nextRow: TableRowValue = existing
      ? { ...existing, [columnCode]: parsed }
      : { row_code: rowCode, [columnCode]: parsed };

    const nextRows = existing
      ? tableValue.map((row) => (row.row_code === rowCode ? nextRow : row))
      : [...tableValue, nextRow];

    onChange?.(nextRows);
  };

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <div
        className={cn(
          "overflow-x-auto rounded-lg border-[1.5px]",
          error ? "border-[#B3403B]" : "border-[#8891A3]"
        )}
      >
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
                  {column.is_required && (
                    <span className="ml-1 text-[#B3403B]">*</span>
                  )}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>

          <TableBody>
            {rows.length > 0 ? (
              rows.map((row) => (
                <TableRowItem
                  key={row.id}
                  rowLabel={row.label}
                  rowCode={row.code}
                  columns={columns}
                  rowValue={valueByRowCode.get(row.code)}
                  disabled={disabled}
                  readOnly={readOnly}
                  onCommit={commitCell}
                />
              ))
            ) : (
              <TableRow>
                <UiTableCell
                  colSpan={Math.max(columns.length + 1, 1)}
                  className="py-8 text-center text-sm text-[#6B7280]"
                >
                  No fixed rows defined.
                </UiTableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {rows.length === 0 && (
        <p className="text-xs text-[#6B7280]">
          Dynamic rows will be added by the future M5 data-capture workflow.
        </p>
      )}
    </FieldWrapper>
  );
}