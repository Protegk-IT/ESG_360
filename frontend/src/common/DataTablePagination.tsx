import type { Table } from "@tanstack/react-table";

import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";

import { Button } from "@/components/ui/button";

interface DataTablePaginationProps<TData> {
  table: Table<TData>;
}

export function DataTablePagination<TData>({
  table,
}: DataTablePaginationProps<TData>) {
  return (
    <div className="flex w-full flex-wrap items-center justify-between gap-3">

      <div className="text-sm text-muted-foreground">
        Showing{" "}
        <strong>
          {table.getRowModel().rows.length}
        </strong>{" "}
        of{" "}
        <strong>
          {table.getCoreRowModel().rows.length}
        </strong>{" "}
        rows
      </div>

      <div className="flex items-center gap-2">

        <Button
          variant="outline"
          size="icon"
          onClick={() => table.firstPage()}
          disabled={!table.getCanPreviousPage()}
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <span className="whitespace-nowrap text-sm font-medium">
          Page{" "}
          <strong>
            {table.getState().pagination.pageIndex + 1}
          </strong>{" "}
          of{" "}
          <strong>
            {table.getPageCount()}
          </strong>
        </span>

        <Button
          variant="outline"
          size="icon"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => table.lastPage()}
          disabled={!table.getCanNextPage()}
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>

      </div>

    </div>
  );
}