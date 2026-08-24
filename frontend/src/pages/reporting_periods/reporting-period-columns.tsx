import type { ColumnDef } from "@tanstack/react-table";

import {
  CalendarRange,
  MoreHorizontal,
  Pencil,
  Trash2,
  Eye,
  Lock,
  Unlock,
  GitBranch,
} from "lucide-react";

import type { ReportingPeriod } from "@/types/reporting-period";

import { Badge } from "@/components/ui/badge";

import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ReportingPeriodColumnsProps {
  onView?: (id: string) => void;

  onEdit: (id: string) => void;

  onDelete: (period: ReportingPeriod) => void;

  onLock: (period: ReportingPeriod) => void;

  onUnlock: (period: ReportingPeriod) => void;

  onGenerate: (period: ReportingPeriod) => void;
  canGenerate: (period: ReportingPeriod) => boolean;
}

export const getReportingPeriodColumns = ({
  onView,
  onEdit,
  onDelete,
  onLock,
  onUnlock,
  onGenerate,
  canGenerate,
}: ReportingPeriodColumnsProps): ColumnDef<ReportingPeriod>[] => [
  {
    accessorKey: "name",

    header: "Reporting Period",

    cell: ({ row }) => {
      const period = row.original;

      return (
        <div className="flex items-center gap-3">

          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EEF2FF]">

            <CalendarRange className="h-5 w-5 text-[#4A3FD6]" />

          </div>

          <div>

            <p className="font-semibold text-[#22243A]">

              {period.name}

            </p>

            <p className="text-xs text-[#6B7280]">

              {period.start_date} → {period.end_date}

            </p>

          </div>

        </div>
      );
    },
  },

  {
    accessorKey: "period_type",

    header: "Type",

    cell: ({ row }) => (
      <Badge variant="outline">

        {row.original.period_type.replaceAll("_", " ")}

      </Badge>
    ),
  },

  {
    accessorKey: "status",

    header: "Status",

    cell: ({ row }) => {
      const status = row.original.status;

      return (
        <Badge
          variant={
            status === "OPEN"
              ? "success"
              : status === "LOCKED"
              ? "warning"
              : "destructive"
          }
        >
          {status}
        </Badge>
      );
    },
  },

  {
    accessorKey: "is_baseline_year",

    header: "Baseline",

    cell: ({ row }) =>
      row.original.is_baseline_year ? (
        <Badge variant="system">

          Baseline

        </Badge>
      ) : (
        "-"
      ),
  },

  {
    accessorKey: "is_active",

    header: "Active",

    cell: ({ row }) => (
      <Badge
        variant={
          row.original.is_active
            ? "success"
            : "inactive"
        }
      >
        {row.original.is_active
          ? "Active"
          : "Inactive"}
      </Badge>
    ),
  },

  {
    id: "actions",

    enableSorting: false,

    cell: ({ row }) => {
      const period = row.original;

      return (
        <DropdownMenu>

          <DropdownMenuTrigger asChild>

            <Button
              variant="ghost"
              size="icon"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>

          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">

            {onView && (

              <DropdownMenuItem
                onClick={() =>
                  onView(period.id)
                }
              >
                <Eye className="mr-2 h-4 w-4" />

                View

              </DropdownMenuItem>

            )}

            <DropdownMenuItem
              onClick={() =>
                onEdit(period.id)
              }
            >
              <Pencil className="mr-2 h-4 w-4" />

              Edit

            </DropdownMenuItem>

            {canGenerate(period) && (
              <DropdownMenuItem onClick={() => onGenerate(period)}>
                <GitBranch className="mr-2 h-4 w-4" />
                Generate Sub Periods
              </DropdownMenuItem>
            )}

            <DropdownMenuSeparator />

            {period.status === "OPEN" ? (

              <DropdownMenuItem
                onClick={() =>
                  onLock(period)
                }
              >
                <Lock className="mr-2 h-4 w-4" />

                Lock

              </DropdownMenuItem>

            ) : period.status === "LOCKED" ? (

              <DropdownMenuItem
                onClick={() =>
                  onUnlock(period)
                }
              >
                <Unlock className="mr-2 h-4 w-4" />

                Unlock

              </DropdownMenuItem>

            ) : null}

            <DropdownMenuSeparator />

            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() =>
                onDelete(period)
              }
            >
              <Trash2 className="mr-2 h-4 w-4" />

              Delete

            </DropdownMenuItem>

          </DropdownMenuContent>

        </DropdownMenu>
      );
    },
  },
];
