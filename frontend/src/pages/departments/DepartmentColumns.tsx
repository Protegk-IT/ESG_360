import type { ColumnDef } from "@tanstack/react-table";

import {
  Building,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";

import type { Department } from "@/types/department";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface DepartmentColumnsProps {
  onEdit: (id: number) => void;
  onDelete: (department: Department) => void;
}

export const getDepartmentColumns = ({
  onEdit,
  onDelete,
}: DepartmentColumnsProps): ColumnDef<Department>[] => [
  {
    accessorKey: "name",

    header: "Department",

    cell: ({ row }) => {
      const department = row.original;

      return (
        <div className="flex items-center gap-3">

          <div
            className="
              flex
              h-10
              w-10
              items-center
              justify-center
              rounded-xl
              bg-[#EEF0FF]
            "
          >
            <Building className="h-5 w-5 text-[#4A3FD6]" />
          </div>

          <div>

            <p className="font-semibold text-[#22243A]">
              {department.name}
            </p>

            <p className="text-xs text-[#6B7280]">
              {department.code}
            </p>

          </div>

        </div>
      );
    },
  },

  {
    accessorKey: "company_name",

    header: "Company",

    cell: ({ row }) => (
      <span className="text-[#374151]">
        {row.original.company_name}
      </span>
    ),
  },

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

  {
    id: "actions",

    enableSorting: false,

    cell: ({ row }) => {
      const department =
        row.original;

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
                  onEdit(department.id)
                }
              >
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>

              <DropdownMenuItem
                variant="destructive"
                onClick={() =>
                  onDelete(department)
                }
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>

            </DropdownMenuContent>

          </DropdownMenu>

        </div>
      );
    },
  },
];