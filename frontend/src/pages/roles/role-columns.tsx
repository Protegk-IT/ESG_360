import type { ColumnDef } from "@tanstack/react-table";

import {
  MoreHorizontal,
  Pencil,
  Trash2,
  ShieldCheck,
} from "lucide-react";

import type { Role } from "@/types/role";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface RoleColumnsProps {
  onEdit: (id: number) => void;
  onDelete: (role: Role) => void;
}



export const getRoleColumns = ({
  onEdit,
  onDelete,
}: RoleColumnsProps): ColumnDef<Role>[] => [
  {
    accessorKey: "role_name",

    header: "Role",

    cell: ({ row }) => {
      const role = row.original;

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
            <ShieldCheck className="h-5 w-5 text-[#4A3FD6]" />
          </div>

          <div>
            <p className="font-semibold text-[#22243A]">
              {role.role_name}
            </p>

            <p className="text-xs text-[#6B7280]">
              {role.role_code}
            </p>
          </div>
        </div>
      );
    },
  },

  {
    accessorKey: "description",

    header: "Description",

    cell: ({ row }) => (
      <p className="max-w-sm truncate text-[#6B7280]">
        {row.original.description || "-"}
      </p>
    ),
  },

  {
    accessorKey: "is_system_role",

    header: "Type",

    cell: ({ row }) => (
      <Badge
        className={
          row.original.is_system_role
            ? ""
            : ""
        }
        variant={
          row.original.is_system_role
            ? "system"
            : "warning"
        }
      >
        {row.original.is_system_role
          ? "System"
          : "Custom"}
      </Badge>
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
    id: "permissions",

    header: "Permissions",

    cell: ({ row }) => (
      <div className="text-center">
        <Badge variant="secondary">
          {row.original.permissions.length}
        </Badge>
      </div>
    ),
  },

  {
    id: "actions",

    enableSorting: false,

    cell: ({ row }) => {
      const role = row.original;

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
                  onEdit(role.id)
                }
              >
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>

              {!role.is_system_role && (
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() =>
                    onDelete(role)
                  }
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              )}

            </DropdownMenuContent>

          </DropdownMenu>
        </div>
      );
    },
  },
];