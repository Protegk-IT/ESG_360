import type { ColumnDef } from "@tanstack/react-table";

import { Building2, MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import type { OrgNode } from "@/types/organization";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface OrganizationColumnsProps {
  onEdit: (id: string) => void;
  onDelete: (node: OrgNode) => void;
}

export const getOrganizationColumns = ({
  onEdit,
  onDelete,
}: OrganizationColumnsProps): ColumnDef<OrgNode>[] => [
  {
    accessorKey: "name",

    header: "Organization",

    // Always visible — this is the one column a user needs to identify
    // the row, so it never hides on smaller screens.
    cell: ({ row }) => {
      const node = row.original;

      return (
    <div className="flex items-center gap-3 overflow-hidden">

  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF0FF]">
    <Building2 className="h-5 w-5 text-[#4A3FD6]" />
  </div>

  <div className="min-w-0 flex-1">

    <p className="truncate font-semibold text-[#22243A]">
      {node.name}
    </p>

    <p className="truncate text-xs text-[#6B7280]">
      {node.code}
    </p>

  </div>

</div>
      );
    },
  },

  {
    accessorKey: "node_type",

    header: "Node Type",

    // Hidden below sm — still readable via the row's own detail view.
    meta: { className: "hidden sm:table-cell" },

    cell: ({ row }) => (
      <Badge variant="outline">{row.original.node_type.replaceAll("_", " ")}</Badge>
    ),
  },


  {
    accessorKey: "parent_name",

    header: "Parent",

    meta: { className: "hidden lg:table-cell" },

    cell: ({ row }) => <p className="max-w-[180px] truncate text-[#6B7280]">{row.original.parent_name ?? "-"}</p>,
  },

  {
    accessorKey: "is_active",

    header: "Status",

    // Always visible — status is a primary signal even on mobile.
    cell: ({ row }) => (
      <Badge variant={row.original.is_active ? "success" : "destructive"}>
        {row.original.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },

  {
    id: "actions",
    size: 70,

    enableSorting: false,

    cell: ({ row }) => {
      const node = row.original;

      return (
        <div className="flex justify-center">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(node.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>

              <DropdownMenuItem variant="destructive" onClick={() => onDelete(node)}>
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