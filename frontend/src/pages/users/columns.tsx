import type { ColumnDef } from "@tanstack/react-table";
import {
  MoreHorizontal,
  Pencil,
  Trash2,
  Eye,
} from "lucide-react";

import type { UserData } from "@/types/user";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface UserColumnsProps {
  onEdit: (id: number) => void;
  onDelete: (user: UserData) => void;
  onView?: (id: number) => void;
}

export const getUserColumns = ({
  onEdit,
  onDelete,
  onView,
}: UserColumnsProps): ColumnDef<UserData>[] => [
  {
    accessorKey: "full_name",
    header: "Name",

    cell: ({ row }) => (
      <div className="font-medium">
        {row.original.full_name}
      </div>
    ),
  },

  {
    accessorKey: "employee_code",
    header: "Emp Code",
  },

  {
    accessorKey: "email",
    header: "Email",
  },

  {
    accessorKey: "mobile_number",
    header: "Contact",

    cell: ({ row }) =>
      row.original.mobile_number || "-",
  },

  {
    accessorKey: "role_name",
    header: "Role",
cell: ({ row }) => (
  <Badge variant="system">
    {row.original.role_name}
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

    header: "",

    enableSorting: false,

    enableHiding: false,

    cell: ({ row }) => {
      const user = row.original;

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
                  onView(user.id)
                }
              >
                <Eye className="mr-2 h-4 w-4" />
                View
              </DropdownMenuItem>
            )}

            <DropdownMenuItem
              onClick={() =>
                onEdit(user.id)
              }
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() =>
                onDelete(user)
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