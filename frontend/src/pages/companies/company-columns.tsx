import type { ColumnDef } from "@tanstack/react-table";

import {
  Building2,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";

import type { Company } from "@/types/company";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface CompanyColumnsProps {
  onEdit: (id: string) => void;
  onDelete: (company: Company) => void;

  countryMap: Record<string, string>;
}

export const getCompanyColumns = ({
  onEdit,
  onDelete,
  countryMap,
}: CompanyColumnsProps): ColumnDef<Company>[] => [
  {
    accessorKey: "company_name",
    header: "Company",

    cell: ({ row }) => {
      const company = row.original;

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
              bg-[#EEF2FF]
            "
          >
            <Building2 className="h-5 w-5 text-[#4A3FD6]" />
          </div>

          <div>
            <p className="font-semibold text-[#22243A]">
              {company.company_name}
            </p>

            <p className="text-xs text-[#6B7280]">
              {company.company_code}
            </p>
          </div>
        </div>
      );
    },
  },

  {
    accessorKey: "email",
    header: "Email",
  },

  {
    accessorKey: "mobile_number",
    header: "Phone",
  },

  {
    accessorKey: "billing_country",
    header: "Country",

    cell: ({ row }) => {
      const countryId = row.original.billing_country;

      if (!countryId) {
        return "-";
      }

      return countryMap[countryId] ?? "-";
    },
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
      const company = row.original;

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
            <DropdownMenuItem
              onClick={() =>
                onEdit(company.id)
              }
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>

            <DropdownMenuItem
              variant="destructive"
              onClick={() =>
                onDelete(company)
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