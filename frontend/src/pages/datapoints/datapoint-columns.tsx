import type { ColumnDef } from "@tanstack/react-table";

import {
  Eye,
  MoreHorizontal,
  Pencil,
} from "lucide-react";

import type { Datapoint } from "@/types/datapoint";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface DatapointColumnsProps {
  onView: (id: string) => void;
  onEdit: (id: string) => void;
  getCategoryName: (categoryId: string) => string;
  canManage: boolean;
}

export const getDatapointColumns = ({
  onView,
  onEdit,
  getCategoryName,
  canManage,
}: DatapointColumnsProps): ColumnDef<Datapoint>[] => [
  /* ==========================================================
     DATAPOINT
  ========================================================== */

  {
    accessorKey: "label",

    header: "Datapoint",

    cell: ({ row }) => {
      const datapoint = row.original;

      return (
        <div>
          <p className="font-semibold text-[#22243A]">
            {datapoint.label}
          </p>

          <p className="text-xs text-[#6B7280]">
            {datapoint.code}
          </p>
        </div>
      );
    },
  },

  /* ==========================================================
     CATEGORY
  ========================================================== */

  {
    accessorKey: "category",

    header: "Category",

    cell: ({ row }) => {
      const categoryId = row.original.category;

      return (
        <span className="text-sm text-[#4B5563]">
          {getCategoryName(categoryId)}
        </span>
      );
    },
  },



  /* ==========================================================
     DATA TYPE
  ========================================================== */

  {
    accessorKey: "data_type",

    header: "Data Type",

    cell: ({ row }) => (
      <Badge variant="info">
        {formatDataType(row.original.data_type)}
      </Badge>
    ),
  },

  /* ==========================================================
     COLLECTION LEVEL
  ========================================================== */

  {
    accessorKey: "collection_level",

    header: "Collection Level",

    cell: ({ row }) => (
      <Badge variant="outline">
        {formatCollectionLevel(
          row.original.collection_level
        )}
      </Badge>
    ),
  },

  /* ==========================================================
     FREQUENCY
  ========================================================== */

  {
    accessorKey: "frequency",

    header: "Frequency",

    cell: ({ row }) => (
      <Badge variant="purple">
        {formatFrequency(row.original.frequency)}
      </Badge>
    ),
  },


  /* ==========================================================
     STATUS
  ========================================================== */

  {
    accessorKey: "is_active",

    header: "Status",

    cell: ({ row }) => (
      <Badge
        variant={
          row.original.is_active
            ? "success"
            : "destructive"
        }
      >
        {row.original.is_active
          ? "Active"
          : "Inactive"}
      </Badge>
    ),
  },

  /* ==========================================================
     ACTIONS
  ========================================================== */

  {
    id: "actions",

    header: "",

    enableSorting: false,

    cell: ({ row }) => {
      const datapoint = row.original;

      return (
        <div className="flex justify-center">
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
                            <DropdownMenuItem
                onClick={() =>
                  onView(datapoint.id)
                }
              >
                <Eye className="mr-2 h-4 w-4" />
                View
              </DropdownMenuItem>

              {canManage && (
                <DropdownMenuItem
                  onClick={() =>
                    onEdit(datapoint.id)
                  }
                >
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    },
  },
];

/* ==========================================================
   FORMATTERS
========================================================== */

function formatDataType(
  value: Datapoint["data_type"]
) {
  const labels: Record<
    Datapoint["data_type"],
    string
  > = {
    DECIMAL: "Decimal",
    INTEGER: "Integer",
    TEXT: "Text",
    LONG_TEXT: "Long Text",
    BOOLEAN: "Boolean",
    SELECT: "Select",
    DATE: "Date",
    TABLE: "Table",
  };

  return labels[value] ?? value;
}

function formatCollectionLevel(
  value: Datapoint["collection_level"]
) {
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}

function formatFrequency(
  value: Datapoint["frequency"]
) {
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}
