

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

type TableRowValue = Record<string, unknown> & {
  id?: string;
  row_code?: string | null;
  is_dynamic?: boolean;
};

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

function parseCellValue(column: DatapointTableColumn | undefined, rawValue: unknown): unknown {
  if (!column) return rawValue;

  switch (column.data_type) {
    case "INTEGER":
      return parseNumeric("INTEGER", String(rawValue ?? ""));
    case "DECIMAL":
      return parseNumeric("DECIMAL", String(rawValue ?? ""));
    case "BOOLEAN":
      return rawValue === true;
    case "DATE":
      return rawValue === "" || rawValue == null ? null : String(rawValue);
    case "TEXT":
    case "LONG_TEXT":
      return rawValue === "" || rawValue == null ? null : String(rawValue);
    default:
      // SELECT / TABLE: no parsing rule defined yet — pass through.
      return rawValue;
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
  isDynamic,
  column,
  value,
  disabled,
  readOnly,
  onCommit,
}: {
  rowKey: string;
  isDynamic: boolean;
  column: DatapointTableColumn;
  value: unknown;
  disabled?: boolean;
  readOnly?: boolean;
  onCommit: (rowKey: string, isDynamic: boolean, columnCode: string, rawValue: unknown) => void;
}) {
  const isInteractive = !disabled && !readOnly;

  switch (column.data_type) {
    case "INTEGER":
    case "DECIMAL":
      return (
        <NumericInput
          kind={column.data_type}
          value={value}
          disabled={disabled}
          readOnly={readOnly}
          hasError={false}
          cell
          onCommit={(rawValue) => onCommit(rowKey, isDynamic, column.code, rawValue)}
        />
      );

    case "BOOLEAN":
      return (
        <div className="flex h-9 min-w-[100px] items-center">
          <Checkbox
            checked={value === true}
            disabled={disabled}
            aria-readonly={readOnly || undefined}
            onCheckedChange={(next) => {
              if (!isInteractive) return;
              onCommit(rowKey, isDynamic, column.code, next === true);
            }}
          />
        </div>
      );

    case "DATE":
      return (
        <Input
          type="date"
          value={typeof value === "string" ? value : ""}
          disabled={disabled}
          readOnly={readOnly}
          onChange={(event) => {
            if (!isInteractive) return;
            onCommit(rowKey, isDynamic, column.code, event.target.value);
          }}
          className={getFieldClassName({ hasError: false, readOnly, cell: true })}
        />
      );

    case "LONG_TEXT":
      return (
        <TextCellInput
          multiline
          value={value}
          disabled={disabled}
          readOnly={readOnly}
          onCommit={(rawValue) => onCommit(rowKey, isDynamic, column.code, rawValue)}
        />
      );

    case "TEXT":
      return (
        <TextCellInput
          value={value}
          disabled={disabled}
          readOnly={readOnly}
          onCommit={(rawValue) => onCommit(rowKey, isDynamic, column.code, rawValue)}
        />
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
  onCommit,
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
  onCommit: (rowKey: string, isDynamic: boolean, columnCode: string, rawValue: unknown) => void;
  onRemove?: () => void;
  showActionsColumn: boolean;
}) {
  return (
    <TableRow>
      <UiTableCell className="font-semibold text-[#22243A]">{rowLabel}</UiTableCell>

      {columns.map((column) => (
        <UiTableCell key={column.id}>
          <DataCell
            rowKey={rowKey}
            isDynamic={isDynamic}
            column={column}
            value={rowValue?.[column.code]}
            disabled={disabled}
            readOnly={readOnly}
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

  const valueByRowCode = useMemo(() => {
    const map = new Map<string, TableRowValue>();
    for (const row of tableValue) {
      if (!row.is_dynamic && typeof row.row_code === "string") {
        map.set(row.row_code, row);
      }
    }
    return map;
  }, [tableValue]);

  const dynamicRows = useMemo(
    () => tableValue.filter((row) => row.is_dynamic === true),
    [tableValue]
  );

  const columnByCode = useMemo(() => {
    const map = new Map<string, DatapointTableColumn>();
    for (const column of columns) map.set(column.code, column);
    return map;
  }, [columns]);

  const allowDynamicRows = Boolean(datapoint.allow_dynamic_rows);
  const canEdit = !disabled && !readOnly;

  const commitCell = (
    rowKey: string,
    isDynamic: boolean,
    columnCode: string,
    rawValue: unknown
  ) => {
    const parsed = parseCellValue(columnByCode.get(columnCode), rawValue);

    const existingIndex = tableValue.findIndex((row) =>
      isDynamic ? row.id === rowKey : !row.is_dynamic && row.row_code === rowKey
    );

    if (existingIndex === -1) {
      const newRow: TableRowValue = isDynamic
        ? { id: rowKey, row_code: null, is_dynamic: true, [columnCode]: parsed }
        : { id: `fixed:${rowKey}`, row_code: rowKey, is_dynamic: false, [columnCode]: parsed };
      onChange?.([...tableValue, newRow]);
      return;
    }

    const nextRows = tableValue.map((row, index) =>
      index === existingIndex ? { ...row, [columnCode]: parsed } : row
    );
    onChange?.(nextRows);
  };

  const addDynamicRow = () => {
    const newRow: TableRowValue = {
      id: generateRowId(),
      row_code: null,
      is_dynamic: true,
    };
    onChange?.([...tableValue, newRow]);
  };

  const removeDynamicRow = (id: string) => {
    onChange?.(tableValue.filter((row) => row.id !== id));
  };

  const showActionsColumn = allowDynamicRows;
  const totalColSpan = Math.max(columns.length + 1 + (showActionsColumn ? 1 : 0), 1);

  return (
    <FieldWrapper datapoint={datapoint} required={required} error={error}>
      <div
        className={cn(
          "overflow-hidden rounded-lg border-[1.5px]",
          error ? "border-[#B3403B]" : "border-[#8891A3]"
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
                  rowKey={row.code}
                  isDynamic={false}
                  columns={columns}
                  rowValue={valueByRowCode.get(row.code)}
                  disabled={disabled}
                  readOnly={readOnly}
                  onCommit={commitCell}
                  showActionsColumn={showActionsColumn}
                />
              ))}

              {dynamicRows.map((rowValue, index) => (
                <TableRowItem
                  key={String(rowValue.id)}
                  rowLabel={`Row ${index + 1}`}
                  rowKey={String(rowValue.id)}
                  isDynamic
                  columns={columns}
                  rowValue={rowValue}
                  disabled={disabled}
                  readOnly={readOnly}
                  onCommit={commitCell}
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