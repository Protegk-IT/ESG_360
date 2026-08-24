import { useMemo } from "react";

import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, Trash2 } from "lucide-react";

import type {
  DatapointTableColumn,
  DatapointTableRow,
  ValidationMetadata,
} from "@/types/datapoint";
import {
  validateValue,
  validateRowCount,
  type CellPrimitive,
} from "@/pages/datapoints/TableDatapointvalidation";

/* ==========================================================
   VALUE SHAPE
   ----------------------------------------------------------
   `key` is the row identity: a fixed row's `code` for
   pre-defined rows, or a client-generated key for a row added
   at answer time. This is deliberately generic so M5 can map
   each TableAnswerRow -> AnswerTableRow (key -> row FK or null
   for dynamic rows + an ordinal) and each entry in `cells` ->
   an AnswerTableCell, without the renderer itself changing.
========================================================== */

export interface TableAnswerRow {
  key: string;
  /** Free-text label for a dynamically added row. Fixed rows always take
   *  their label from the matching DatapointTableRow instead. */
  label?: string;
  isDynamic: boolean;
  cells: Record<string, CellPrimitive>; // column code -> value
}

export type TableAnswerValue = TableAnswerRow[];

interface TableAnswerRendererProps {
  columns: DatapointTableColumn[];
  fixedRows: DatapointTableRow[];
  allowDynamicRows: boolean;
  /** The Datapoint's own validation_metadata — for dynamic tables this is
   *  where min_rows/max_rows live. Ignored for fixed-row tables. */
  tableValidation: ValidationMetadata;
  value: TableAnswerValue;
  onChange: (next: TableAnswerValue) => void;
}

let dynamicRowCounter = 0;
function nextDynamicKey() {
  dynamicRowCounter += 1;
  return `__new_row_${Date.now()}_${dynamicRowCounter}`;
}

export function TableAnswerRenderer({
  columns,
  fixedRows,
  allowDynamicRows,
  tableValidation,
  value,
  onChange,
}: TableAnswerRendererProps) {
  const sortedColumns = useMemo(
    () => [...columns].sort((a, b) => a.display_order - b.display_order),
    [columns]
  );

  // Fixed rows always render, in display order, seeded from `value` if
  // already present; any dynamic rows the user added ride along after them.
  const rows = useMemo<TableAnswerRow[]>(() => {
    const byKey = new Map(value.map((r) => [r.key, r]));
    const fixed = [...fixedRows]
      .sort((a, b) => a.display_order - b.display_order)
      .map<TableAnswerRow>(
        (r) => byKey.get(r.code) ?? { key: r.code, isDynamic: false, cells: {} }
      );
    const dynamic = value.filter((r) => r.isDynamic);
    return [...fixed, ...dynamic];
  }, [value, fixedRows]);

  const rowCountError = allowDynamicRows
    ? validateRowCount(rows.length, tableValidation)
    : null;

  const setCell = (rowKey: string, columnCode: string, cellValue: CellPrimitive) => {
    onChange(
      rows.map((row) =>
        row.key === rowKey
          ? { ...row, cells: { ...row.cells, [columnCode]: cellValue } }
          : row
      )
    );
  };

  const addDynamicRow = () => {
    onChange([...rows, { key: nextDynamicKey(), isDynamic: true, cells: {} }]);
  };

  const removeDynamicRow = (rowKey: string) => {
    onChange(rows.filter((row) => row.key !== rowKey));
  };

  const rowLabel = (row: TableAnswerRow) =>
    row.isDynamic
      ? row.label ?? "New row"
      : fixedRows.find((r) => r.code === row.key)?.label ?? row.key;

  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Row</TableHead>
            {sortedColumns.map((col) => (
              <TableHead key={col.id}>
                {col.label}
                {col.is_required && <span className="text-red-600"> *</span>}
              </TableHead>
            ))}
            {allowDynamicRows && <TableHead className="w-12" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.key}>
              <TableCell className="align-top font-medium">
                {row.isDynamic ? (
                  <Input
                    value={row.label ?? ""}
                    placeholder="Row label"
                    onChange={(e) =>
                      onChange(
                        rows.map((r) =>
                          r.key === row.key ? { ...r, label: e.target.value } : r
                        )
                      )
                    }
                  />
                ) : (
                  rowLabel(row)
                )}
              </TableCell>
              {sortedColumns.map((col) => (
                <TableCell key={col.id} className="align-top">
                  <TableCellInput
                    column={col}
                    value={row.cells[col.code] ?? null}
                    onChange={(v) => setCell(row.key, col.code, v)}
                  />
                </TableCell>
              ))}
              {allowDynamicRows && (
                <TableCell className="align-top">
                  {row.isDynamic && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeDynamicRow(row.key)}
                    >
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={sortedColumns.length + (allowDynamicRows ? 2 : 1)}
                className="py-6 text-center text-sm text-muted-foreground"
              >
                No rows yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {allowDynamicRows && (
        <Button type="button" variant="outline" size="sm" onClick={addDynamicRow}>
          <Plus className="mr-2 h-4 w-4" />
          Add Row
        </Button>
      )}

      {rowCountError && <p className="text-xs text-red-600">{rowCountError}</p>}
    </div>
  );
}

/* ==========================================================
   PER-CELL INPUT
   ----------------------------------------------------------
   Dispatches on column.data_type. A column with data_type ===
   "TABLE" isn't excluded by the type itself (DatapointTableColumn
   just uses the full DatapointDataType) — it's only kept out by
   the column-type picker in DatapointTableDefinitionManager,
   which offers every type except TABLE. If one ever slips through
   some other path, it falls through to `default: return null`
   below rather than crashing.
========================================================== */

function TableCellInput({
  column,
  value,
  onChange,
}: {
  column: DatapointTableColumn;
  value: CellPrimitive;
  onChange: (value: CellPrimitive) => void;
}) {
  const error = validateValue(
    column.data_type,
    column.validation_metadata ?? {},
    value,
    column.is_required
  );
  const errorNode = error ? <p className="mt-1 text-xs text-red-600">{error}</p> : null;

  switch (column.data_type) {
    case "DECIMAL":
    case "INTEGER":
      return (
        <div>
          <Input
            type="number"
            step={column.data_type === "DECIMAL" ? "any" : "1"}
            value={typeof value === "number" ? value : ""}
            onChange={(e) =>
              onChange(e.target.value === "" ? null : Number(e.target.value))
            }
          />
          {errorNode}
        </div>
      );

    case "BOOLEAN":
      return (
        <Checkbox
          checked={value === true}
          onCheckedChange={(checked) => onChange(checked === true)}
        />
      );

    case "DATE":
      return (
        <div>
          <Input
            type="date"
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
          />
          {errorNode}
        </div>
      );

    case "TEXT":
      return (
        <div>
          <Input
            type="text"
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
          />
          {errorNode}
        </div>
      );

    case "LONG_TEXT":
      return (
        <div>
          <textarea
            className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
            rows={2}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
          />
          {errorNode}
        </div>
      );

    case "SELECT":
      // CONTRACT GAP, scoped to table columns specifically: DatapointOption
      // (the model that carries an option's code/label/display_order) has a
      // ForeignKey to Datapoint, not to DatapointTableColumn — so a SELECT
      // *column inside a TABLE* has nowhere to source its choice list from
      // today, even though a top-level SELECT datapoint does. Falling back
      // to free text here rather than inventing options; wire this up to a
      // real <Select> once DatapointTableColumn (or a parallel model) gets
      // its own option list.
      return (
        <div>
          <Input
            type="text"
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
          />
          <p className="mt-1 text-xs text-amber-600">
            No option list available for SELECT table columns yet — free
            text for now.
          </p>
        </div>
      );

    default:
      return null;
  }
}