import type {
  DatapointTableColumn,
  DatapointTableRow,
} from "@/types/datapoint";

import type {
  AnswerTableCell,
  AnswerTableRow,
  TableCellWritePayload,
  TableRowWritePayload,
} from "@/types/dataCapture";

import {
  emptyTableCell,
  fixedRowDraft,
  type TableAnswerDraft,
  type TableCellDraft,
  type TableRowDraft,
} from "@/pages/datapoints/tableAnswerAdapter";

/* ==========================================================
   M5 ANSWER TABLE → M4 TABLE DRAFT
   ----------------------------------------------------------
   Converts normalized M5 AnswerTableRow/AnswerTableCell
   responses into the exact TableAnswerDraft consumed by
   the existing M4 TableField.

   M5:
     AnswerTableRow[]
       └── AnswerTableCell[]

   M4:
     TableAnswerDraft
       └── TableRowDraft[]
            └── TableCellDraft[]
========================================================== */

export function answerTableRowsToDraft(
  rows: AnswerTableRow[],
): TableAnswerDraft {
  return rows
    .map((row): TableRowDraft => ({
      id: row.id,
      definition_row: row.definition_row,
      label: row.label,
      display_order: row.display_order,
      cells: row.cells.map(answerTableCellToDraft),
    }))
    .sort(
      (a, b) => a.display_order - b.display_order,
    );
}

/* ==========================================================
   M5 CELL → M4 CELL
========================================================== */

function answerTableCellToDraft(
  cell: AnswerTableCell,
): TableCellDraft {
  return {
    column: cell.column,

    decimal_value: normalizeDecimal(
      cell.decimal_value,
    ),

    integer_value:
      cell.integer_value,

    text_value:
      cell.text_value,

    boolean_value:
      cell.boolean_value,

    date_value:
      cell.date_value,

    unit:
      cell.unit,
  };
}
/* ==========================================================
   M4 TABLE DRAFT → M5 TABLE ROW PAYLOADS
   ----------------------------------------------------------
   Converts the existing M4 TableField value into the
   normalized M5 row/cell write contract.

   The entire table is NEVER serialized as JSON.
========================================================== */

export function tableDraftToRowPayloads(
  draft: TableAnswerDraft,
): TableRowWritePayload[] {
  return draft.map((row) => ({
    definition_row: row.definition_row,
    label: row.label,
    display_order: row.display_order,

    cells: row.cells.map(
      tableCellDraftToWritePayload,
    ),
  }));
}

/* ==========================================================
   M4 CELL → M5 CELL
   ----------------------------------------------------------
   text_value defaults to "" rather than null: the backend's
   AnswerTableCell.text_value column is NOT NULL (the standard
   Django convention — string fields use "" as their empty
   sentinel, never None). emptyTableCell() leaves text_value
   unset entirely on a fresh cell, so cell.text_value is
   undefined for any untouched cell — "?? null" was previously
   forwarding that as an explicit null on every save, tripping
   an IntegrityError on essentially any table save that didn't
   touch every single cell in the row.

   selected_option is intentionally omitted: TableCellDraft
   types it as `never` (see tableAnswerAdapter.ts) since M5
   deliberately rejects it until M4 has column-level SELECT
   options — sending selected_option: null on every cell
   contradicted that documented contract, even though it
   likely wasn't causing an error today.
========================================================== */

function tableCellDraftToWritePayload(
  cell: TableCellDraft,
): TableCellWritePayload {
  return {
    column: cell.column,

    decimal_value:
      cell.decimal_value ?? null,

    integer_value:
      cell.integer_value ?? null,

    text_value:
      cell.text_value ?? "",

    boolean_value:
      cell.boolean_value ?? null,

    date_value:
      cell.date_value ?? null,

    unit:
      cell.unit ?? null,
  };
}



/* ==========================================================
   FIXED ROW HYDRATION
   ----------------------------------------------------------
   Ensures M4-defined fixed rows exist even when the M5
   answer has not created a saved AnswerTableRow yet.

   Existing M5 rows are matched using definition_row.
========================================================== */

export function hydrateTableDraft(
  savedRows: AnswerTableRow[],
  definitionRows: DatapointTableRow[],
  columns: DatapointTableColumn[],
): TableAnswerDraft {
  const savedByDefinitionRow = new Map<
    string,
    AnswerTableRow
  >();

  const dynamicRows: AnswerTableRow[] = [];

  for (const row of savedRows) {
    if (row.definition_row) {
      savedByDefinitionRow.set(
        row.definition_row,
        row,
      );
    } else {
      dynamicRows.push(row);
    }
  }

  const fixedRows: TableRowDraft[] =
    definitionRows
      .slice()
      .sort(
        (a, b) =>
          a.display_order - b.display_order,
      )
      .map((definitionRow) => {
        const savedRow =
          savedByDefinitionRow.get(
            definitionRow.id,
          );

        if (savedRow) {
          return {
            id: savedRow.id,
            definition_row:
              savedRow.definition_row,
            label: savedRow.label,
            display_order:
              savedRow.display_order,
            cells: hydrateCells(
              savedRow.cells,
              columns,
            ),
          };
        }

        return {
          ...fixedRowDraft(definitionRow),
          cells: columns.map(
            emptyTableCell,
          ),
        };
      });

  const hydratedDynamicRows: TableRowDraft[] =
    dynamicRows
      .slice()
      .sort(
        (a, b) =>
          a.display_order - b.display_order,
      )
      .map((row) => ({
        id: row.id,
        definition_row: null,
        label: row.label,
        display_order: row.display_order,
        cells: hydrateCells(
          row.cells,
          columns,
        ),
      }));

  return [
    ...fixedRows,
    ...hydratedDynamicRows,
  ];
}

/* ==========================================================
   CELL HYDRATION
   ----------------------------------------------------------
   Makes sure every M4-defined column has a cell while
   preserving existing M5 values and IDs.
========================================================== */

function hydrateCells(
  savedCells: AnswerTableCell[],
  columns: DatapointTableColumn[],
): TableCellDraft[] {
  const savedByColumn = new Map(
    savedCells.map((cell) => [
      cell.column,
      cell,
    ]),
  );

  return columns
    .slice()
    .sort(
      (a, b) =>
        a.display_order - b.display_order,
    )
    .map((column) => {
      const savedCell =
        savedByColumn.get(column.id);

      if (!savedCell) {
        return emptyTableCell(column);
      }

      return answerTableCellToDraft(
        savedCell,
      );
    });
}

/* ==========================================================
   DECIMAL NORMALIZATION
   ----------------------------------------------------------
   DRF DecimalField may be returned as a string.
   M4 TableField expects number | null.
========================================================== */

function normalizeDecimal(
  value: string | number | null,
): number | null {
  if (value === null) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value)
      ? value
      : null;
  }

  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}