import {
  ChevronRight,
  ChevronDown,
  MoreVertical,
  Pencil,
  Trash2,
  Plus,
  ArrowRightLeft,
  Leaf,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

import type { OrgNode } from "@/types/organization";
import { NODE_TYPE_CONFIG } from "./nodeTypeConfig";

interface OrgTreeRowProps {
  node: OrgNode;
  depth: number;
  isExpanded: (id: string) => boolean;
  onToggle: (id: string) => void;
  onAddChild: (parent: OrgNode) => void;
  onEdit: (node: OrgNode) => void;
  onMove: (node: OrgNode) => void;
  onDelete: (node: OrgNode) => void;
}

export function OrgTreeRow({
  node,
  depth,
  isExpanded,
  onToggle,
  onAddChild,
  onEdit,
  onMove,
  onDelete,
}: OrgTreeRowProps) {
  const children = node.children ?? [];
  const hasChildren = children.length > 0;
  const expanded = isExpanded(node.id);
  const config = NODE_TYPE_CONFIG[node.node_type] ?? NODE_TYPE_CONFIG.FACILITY;
  const Icon = config.icon;

  return (
    <div>
      <div
        className="group flex flex-wrap items-center gap-2 rounded-xl border border-transparent px-2 py-2.5 hover:border-[#E5E7EB] hover:bg-[#FAFBFA] sm:flex-nowrap sm:gap-3 sm:px-3 sm:py-3"
        // Smaller step on mobile so a 4-level tree doesn't push
        // content off-screen; scales up at sm and above.
        style={{ paddingLeft: `calc(${depth} * clamp(14px, 4vw, 24px) + 8px)` }}
      >
        <button
          type="button"
          onClick={() => hasChildren && onToggle(node.id)}
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border sm:h-8 sm:w-8 ${
            hasChildren
              ? "border-[#E5E7EB] bg-white text-[#6B7280] hover:bg-gray-50"
              : "invisible"
          }`}
        >
          {hasChildren &&
            (expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />)}
        </button>

        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl sm:h-11 sm:w-11 ${config.iconBg}`}
        >
          <Icon className={`h-4 w-4 sm:h-5 sm:w-5 ${config.iconColor}`} />
        </div>

        <div className="min-w-0 flex-1 basis-[140px]">
          <p className="truncate text-sm font-semibold text-[#22243A] sm:text-base">{node.name}</p>
          <p className="truncate text-xs text-[#9CA3AF]">{node.code}</p>
        </div>

        <Badge
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium sm:px-3 sm:py-1 ${config.badgeClass}`}
        >
          {config.label}
        </Badge>

        {/* Icon-only on mobile, icon+text from sm up */}
        <div className="flex shrink-0 items-center gap-1.5 text-[#16A34A]">
          <Leaf className="h-4 w-4" />
          <span className="hidden text-sm font-medium sm:inline">
            {node.is_active ? "Active" : "Inactive"}
          </span>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto shrink-0 rounded-lg border border-[#E5E7EB] sm:ml-0"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {config.defaultChildType && (
              <DropdownMenuItem onClick={() => onAddChild(node)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Child
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => onEdit(node)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onMove(node)}>
              <ArrowRightLeft className="mr-2 h-4 w-4" />
              Move
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={() => onDelete(node)}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {hasChildren && expanded && (
        <div className="ml-[28px] border-l-2 border-[#E5E7EB] pl-3 sm:ml-[35px] sm:pl-5">
          {children.map((child) => (
            <div key={child.id} className="relative">
              <span className="absolute -left-3 top-[22px] h-px w-3 bg-[#E5E7EB] sm:-left-5 sm:top-[26px] sm:w-5" />
              <OrgTreeRow
                node={child}
                depth={depth + 1}
                isExpanded={isExpanded}
                onToggle={onToggle}
                onAddChild={onAddChild}
                onEdit={onEdit}
                onMove={onMove}
                onDelete={onDelete}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}