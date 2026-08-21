import { Search, Download, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface DataTableToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;

  children?: React.ReactNode;

  addLabel?: string;
  onAdd?: () => void;

  exportLabel?: string;
  onExport?: () => void;
  className?: string;

  /* ===================================================
     OPTIONAL PER-PAGE OVERRIDES
     ---------------------------------------------------
     All default to the existing look, so pages that don't
     pass them render exactly as before. Use these instead
     of editing the base classes above, so one page's layout
     needs never leak into every other page using this
     shared toolbar.
  =================================================== */

  // Merged onto the search wrapper's own classes (default: "w-full sm:w-80").
  // Use to change just the width, e.g. searchClassName="sm:w-56".
  searchClassName?: string;

  // Merged onto the filters wrapper's own classes.
  filtersClassName?: string;

  // shadcn Button size for both action buttons. Defaults to "default"
  // (current behavior) — pass "sm" for a more compact toolbar.
  actionButtonSize?: "default" | "sm" | "lg" | "icon";

  // Merged onto the Add button's own classes (default: "flex-1 sm:flex-none").
  addButtonClassName?: string;

  // Merged onto the Export button's own classes (default: "flex-1 sm:flex-none").
  exportButtonClassName?: string;
}

export function DataTableToolbar({
  search,
  onSearchChange,

  children,

  addLabel,
  onAdd,

  exportLabel = "Export",
  onExport,
  className,

  searchClassName,
  filtersClassName,
  actionButtonSize = "default",
  addButtonClassName,
  exportButtonClassName,
}: DataTableToolbarProps) {
  return (
    <div
      className={cn(
        `
        mb-6
        flex
        w-full
        flex-col
        gap-4

        sm:flex-row
        sm:items-center
        sm:justify-between
        sm:gap-6
      `,
        className
      )}
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

        <div className={cn("relative w-full shrink-0 sm:w-80", searchClassName)}>
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
          className={cn(
            `
            flex
            items-center
            gap-3
            overflow-x-auto
            whitespace-nowrap
            pb-1

            sm:pb-0
          `,
            filtersClassName
          )}
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
            size={actionButtonSize}
            onClick={onExport}
            className={cn("flex-1 sm:flex-none", exportButtonClassName)}
          >
            <Download className="mr-2 h-4 w-4" />
            {exportLabel}
          </Button>
        )}

        {onAdd && (
          <Button
            size={actionButtonSize}
            onClick={onAdd}
            className={cn("flex-1 sm:flex-none", addButtonClassName)}
          >
            <Plus className="mr-2 h-4 w-4" />
            {addLabel ?? "Add"}
          </Button>
        )}
      </div>
    </div>
  );
}