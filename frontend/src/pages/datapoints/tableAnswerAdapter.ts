import type { DatapointTableColumn, DatapointTableRow } from "@/types/datapoint";

/**
 * Renderer-owned draft state for a TABLE answer.
 *
 * This deliberately uses catalog UUIDs rather than mutable codes.  It is not
 * an API client: an M5 screen can pass this state to `toM5TableRowPayload`
 * when it saves one normalized AnswerTableRow.
 *
 * NOTE (no functional change made in this pass): emptyTableCell() below is
 * correct as-is — it simply omits text_value entirely for a fresh cell
 * rather than defaulting it to null, which is exactly why the sibling file
 * (@/pages/dataCapture/tableAnswerAdapter.ts) needed its own fix: its
 * tableCellDraftToWritePayload was force-filling every field with `?? null`,
 * turning this file's intentionally-absent text_value into an explicit null
 * that violated the backend's NOT NULL constraint on text_value. This file
 * needed no change — only the other one did.
 *
 * Worth a follow-up decision at some point: toM5TableRowPayload here and
 * tableDraftToRowPayloads/tableCellDraftToWritePayload in the other file
 * both convert a TableRowDraft into a write payload, but take different
 * approaches (spread-only-present-keys here vs. force-fill-every-key
 * there). Only one of them is actually wired into the app
 * (tableDraftToRowPayloads, via DataCaptureRequestPage's saveTableRows).
 * Consolidating to a single payload builder — probably this file's
 * spread-based version, since it can't reintroduce the same null-defaulting
 * class of bug — would remove the duplicate-implementation risk, but that's
 * a larger refactor than this bug fix and hasn't been done here.
 */
export interface TableCellDraft {
  column: string;
  decimal_value?: number | null;
  integer_value?: number | null;
  text_value?: string | null;
  boolean_value?: boolean | null;
  date_value?: string | null;
  /** M5 deliberately rejects this until M4 has column-level options. */
  selected_option?: never;
  unit?: string | null;
}

export interface TableRowDraft {
  /** Client key for an unsaved dynamic row; M5 row UUID once persisted. */
  id: string;
  /** UUID of the fixed M4 DatapointTableRow, otherwise null for dynamic rows. */
  definition_row: string | null;
  label: string;
  display_order: number;
  cells: TableCellDraft[];
}

export type TableAnswerDraft = TableRowDraft[];

export function emptyTableCell(column: DatapointTableColumn): TableCellDraft {
  return {
    column: column.id,
    ...(column.default_unit ? { unit: column.default_unit } : {}),
  };
}

export function fixedRowDraft(row: DatapointTableRow): TableRowDraft {
  return {
    id: `definition:${row.id}`,
    definition_row: row.id,
    label: row.label,
    display_order: row.display_order,
    cells: [],
  };
}

/** Exact body accepted by M5's table-row create/update endpoints. */
export function toM5TableRowPayload(row: TableRowDraft) {
  return {
    definition_row: row.definition_row,
    label: row.definition_row ? undefined : row.label,
    display_order: row.display_order,
    cells: row.cells.map(({ column, ...value }) => ({ column, ...value })),
  };
}