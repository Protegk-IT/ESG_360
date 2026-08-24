import { Search, Download, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface DataTableToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;

  children?: React.ReactNode;

  addLabel?: string;
  onAdd?: () => void;

  exportLabel?: string;
  onExport?: () => void;
  className?: string;
}

export function DataTableToolbar({
  search,
  onSearchChange,

  children,

  addLabel,
  onAdd,

  exportLabel = "Export",
  onExport,
}: DataTableToolbarProps) {
  return (
    <div
      className="
        mb-6
        flex
        w-full
        flex-col
        gap-4

        sm:flex-row
        sm:items-center
        sm:justify-between
        sm:gap-6
      "
    >
      {/* =====================================================
          LEFT SECTION
      ===================================================== */}

      <div
        className="
          flex
          min-w-0
          flex-1
          flex-col
          gap-3

          sm:flex-row
          sm:items-center
          sm:gap-4
        "
      >
        {/* Search */}

        <div
          className="
            relative
            w-full
            shrink-0

            sm:w-80
          "
        >
          <Search
            className="
              absolute
              left-3
              top-1/2
              h-4
              w-4
              -translate-y-1/2
              text-[#6B7280]
            "
          />

          <Input
            placeholder="Search..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Filters */}

        <div
          className="
            flex
            items-center
            gap-3
            overflow-x-auto
            whitespace-nowrap
            pb-1

            sm:pb-0
          "
        >
          {children}
        </div>
      </div>

      {/* =====================================================
          ACTION BUTTONS
      ===================================================== */}

      <div
        className="
          flex
          shrink-0
          items-center
          gap-3

          sm:justify-end
        "
      >
        {onExport && (
          <Button
            variant="outline"
            onClick={onExport}
            className="flex-1 sm:flex-none"
          >
            <Download className="mr-2 h-4 w-4" />
            {exportLabel}
          </Button>
        )}

        {onAdd && (
          <Button onClick={onAdd} className="flex-1 sm:flex-none">
            <Plus className="mr-2 h-4 w-4" />
            {addLabel ?? "Add"}
          </Button>
        )}
      </div>
    </div>
  );
}