"use client";

import * as React from "react";

import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";

import { ArrowDown, ArrowUp, ArrowUpDown, Database } from "lucide-react";

import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";

import { Skeleton } from "@/components/ui/skeleton";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { DataTablePagination } from "./DataTablePagination";

// Columns can opt into responsive visibility (e.g. hide on mobile) by
// setting `meta: { className: "hidden md:table-cell" }` in their
// ColumnDef — see OrgColumns.tsx for an example.
export interface DataTableColumnMeta {
  className?: string;
}

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];

  data: TData[];

  loading?: boolean;

  emptyMessage?: string;

  toolbar?: React.ReactNode;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  loading = false,
  emptyMessage = "No records found.",
  toolbar,
}: DataTableProps<TData, TValue>) {
  /* ==========================================================
     TABLE STATE
  ========================================================== */

  const [sorting, setSorting] = React.useState<SortingState>([]);

  /* ==========================================================
     TANSTACK TABLE
  ========================================================== */

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,

    state: {
      sorting,
    },

    onSortingChange: setSorting,

    getCoreRowModel: getCoreRowModel(),

    getSortedRowModel: getSortedRowModel(),

    getPaginationRowModel: getPaginationRowModel(),
  });

  /* ==========================================================
     ESG CARD
  ========================================================== */

  return (
    <Card className="w-full min-w-0 overflow-hidden">
      {/* ============================================
          TOOLBAR
      ============================================ */}

      {toolbar && <CardHeader className="px-4 py-4 sm:px-6 sm:py-6">{toolbar}</CardHeader>}

      {/* ============================================
          TABLE
      ============================================ */}

      <CardContent className="p-0">
        {/* Only this wrapper scrolls horizontally when the table is
            wider than its container — the page itself never scrolls
            sideways because of it. */}
        <div className="w-full overflow-x-auto">
          <Table>
            {/* ==========================================================
                TABLE HEADER
            ========================================================== */}
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="hover:bg-transparent">
                  {headerGroup.headers.map((header) => {
                    const meta = header.column.columnDef.meta as
                      | DataTableColumnMeta
                      | undefined;

                    return (
                      <TableHead
                        key={header.id}
                        onClick={header.column.getToggleSortingHandler()}
                        className={`h-14 px-4 text-sm font-semibold text-[#4B5563] whitespace-nowrap sm:px-6 ${
                          header.column.getCanSort() ? "cursor-pointer select-none" : ""
                        } ${meta?.className ?? ""}`}
                      >
                        <div className="flex items-center gap-2">
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())}

                          {header.column.getCanSort() && (
                            <>
                              {{
                                asc: <ArrowUp className="h-4 w-4 text-slate-400 opacity-70" />,
                                desc: <ArrowDown className="h-4 w-4 text-slate-400 opacity-70" />,
                              }[header.column.getIsSorted() as string] ?? (
                                <ArrowUpDown className="h-4 w-4 text-gray-400" />
                              )}
                            </>
                          )}
                        </div>
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>

            {/* ==========================================================
                TABLE BODY
            ========================================================== */}

            <TableBody>
              {loading ? (
                Array.from({ length: 8 }).map((_, row) => (
                  <TableRow key={row}>
                    {columns.map((column, col) => {
                      const meta = column.meta as DataTableColumnMeta | undefined;

                      return (
                        <TableCell
                          key={col}
                          className={`px-4 py-5 sm:px-6 ${meta?.className ?? ""}`}
                        >
                          <Skeleton className="h-4 w-3/4 rounded-full" />
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))
              ) : table.getRowModel().rows.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id} className="transition-colors hover:bg-[#F5F5FB]">
                    {row.getVisibleCells().map((cell) => {
                      const meta = cell.column.columnDef.meta as
                        | DataTableColumnMeta
                        | undefined;

                      return (
                        <TableCell
                          key={cell.id}
                          className={`px-4 py-5 sm:px-6 ${meta?.className ?? ""}`}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={columns.length} className="h-[320px]">
                    <div className="flex flex-col items-center justify-center">
                      <div className="mb-5 rounded-full bg-[#EEF2FF] p-5">
                        <Database className="h-8 w-8 text-[#4A3FD6]" />
                      </div>

                      <h3 className="text-lg font-semibold text-gray-800">No Records Found</h3>

                      <p className="mt-2 text-sm text-gray-500">{emptyMessage}</p>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      {/* ==========================================================
          FOOTER
      ========================================================== */}

      <CardFooter className="justify-end px-4 py-4 sm:px-6">
        <DataTablePagination table={table} />
      </CardFooter>
    </Card>
  );
}