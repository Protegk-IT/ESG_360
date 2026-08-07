import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import AppShell from "@/components/layout/AppShell";
// ...keep all your other existing imports exactly as they are

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import ConfirmDialog from "@/common/ConfirmDialog";
import { Network, Leaf, Maximize2, Expand, Plus, Search } from "lucide-react";

import OrganizationApi from "@/api/organizations/OrganizationApi";
import type { OrgNode, OrgNodeType } from "@/types/organization";

import { OrgTreeRow } from "./OrgTreeRow";
import OrgNodeFormPanel from "./OrgNodeFormPanel";
import OrgMoveDialog from "./OrgMoveDialog";
import { NODE_TYPE_CONFIG } from "./nodeTypeConfig";

function collectIds(node: OrgNode): string[] {
  return [node.id, ...(node.children ?? []).flatMap(collectIds)];
}

// Keeps a node if it matches, or if any descendant matches (pruning
// non-matching branches while leaving the ancestor chain intact).
function filterTree(node: OrgNode, query: string): OrgNode | null {
  const q = query.trim().toLowerCase();
  if (!q) return node;

  const selfMatch =
    node.name.toLowerCase().includes(q) || node.code.toLowerCase().includes(q);

  if (selfMatch) return node;

  const filteredChildren = (node.children ?? [])
    .map((child) => filterTree(child, query))
    .filter((child): child is OrgNode => child !== null);

  return filteredChildren.length > 0 ? { ...node, children: filteredChildren } : null;
}

export default function OrgTree() {
  const [root, setRoot] = useState<OrgNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<OrgNodeType | "All">("All");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const [formState, setFormState] = useState<{
    open: boolean;
    mode: "create" | "edit";
    parentNode: OrgNode | null;
    editingNode: OrgNode | null;
  }>({ open: false, mode: "create", parentNode: null, editingNode: null });

  const [moveNode, setMoveNode] = useState<OrgNode | null>(null);
  const [deleteNode, setDeleteNode] = useState<OrgNode | null>(null);
  const [deleting, setDeleting] = useState(false);

  /* ==========================================================
      LOAD TREE
  ========================================================== */

  const loadTree = useCallback(async () => {
    try {
      setLoading(true);
      const response = await OrganizationApi.getTree();

      // Defensive: handle either a bare root object or an array
      // wrapping the root (e.g. [ { ...root } ]).
      const raw = response.data;
      const data: OrgNode | undefined = Array.isArray(raw) ? raw[0] : raw;

      if (!data) {
        toast.error("Organization tree is empty.");
        setRoot(null);
        return;
      }

      setRoot(data);

      setExpandedIds((prev) => {
        if (prev.size > 0) return prev;
        const next = new Set<string>([data.id]);
        (data.children ?? []).forEach((c) => next.add(c.id));
        return next;
      });
    } catch (error) {
      console.error(error);
      toast.error("Unable to load organization tree.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  /* ==========================================================
      SEARCH / FILTER
  ========================================================== */

  const filteredRoot = useMemo(() => (root ? filterTree(root, search) : null), [root, search]);

  const searchExpandIds = useMemo(() => {
    if (!filteredRoot || !search.trim()) return null;
    return new Set(collectIds(filteredRoot));
  }, [filteredRoot, search]);

  const isExpanded = useCallback(
    (id: string) => (searchExpandIds ? searchExpandIds.has(id) : expandedIds.has(id)),
    [searchExpandIds, expandedIds]
  );

  const toggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    if (!root) return;
    setExpandedIds(new Set(collectIds(root)));
  }, [root]);

  const collapseAll = useCallback(() => {
    if (!root) return;
    setExpandedIds(new Set([root.id]));
  }, [root]);

  /* ==========================================================
      FORM / MOVE / DELETE HANDLERS
  ========================================================== */

  const openAddChild = (parent: OrgNode) =>
    setFormState({ open: true, mode: "create", parentNode: parent, editingNode: null });

  const openEdit = (node: OrgNode) =>
    setFormState({ open: true, mode: "edit", parentNode: null, editingNode: node });

  const closeForm = () => setFormState((prev) => ({ ...prev, open: false }));

  const confirmDelete = async () => {
    if (!deleteNode) return;
    try {
      setDeleting(true);
      await OrganizationApi.delete(deleteNode.id);
      toast.success("Node deleted successfully.");
      await loadTree();
      setDeleteNode(null);
    } catch (error) {
      console.error(error);
      toast.error("Unable to delete node. Move or remove its children first.");
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
      UI
  ========================================================== */
return (
    <AppShell
      title="Organization Structure"
      description="Explore and manage your organization hierarchy"
    >
      <div className="bg-white p-6">
        {/* Header */}
        {/* Header */}
        <div className="mb-5 flex flex-col gap-4 rounded-2xl bg-gradient-to-r from-[#EAFBF0] to-[#F5FBF7] p-4 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#166534] sm:h-14 sm:w-14">
              <Network className="h-5 w-5 text-white sm:h-7 sm:w-7" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-lg font-bold text-[#14532D] sm:text-2xl">Organization Structure</h1>
                <span className="flex items-center gap-1 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-[#16A34A]">
                  <Leaf className="h-3 w-3" /> ESG
                </span>
              </div>
              <p className="text-xs text-[#6B7280] sm:text-sm">
                Explore and manage your organization hierarchy
              </p>
            </div>
          </div>

          <Button
            className="w-full bg-[#16A34A] hover:bg-[#15803D] sm:w-auto"
            onClick={() => root && openAddChild(root)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Node
          </Button>
        </div>

        {/* Toolbar */}
        <div className="mb-4 flex flex-col gap-3 rounded-2xl border border-[#E5E7EB] bg-white p-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9CA3AF]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes..."
              className="w-full rounded-lg border border-[#E5E7EB] py-2 pl-10 pr-3 text-sm outline-none focus:border-[#16A34A]"
            />
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as OrgNodeType | "All")}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="All">All Types</SelectItem>
                {Object.entries(NODE_TYPE_CONFIG).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>
                    {cfg.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button variant="outline" size="icon" className="shrink-0" onClick={expandAll} title="Expand all">
              <Expand className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="shrink-0"
              onClick={collapseAll}
              title="Collapse all"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        

        {/* Tree card */}
        {/* Tree card — added overflow-x-auto as a safety net so a very
            deep tree scrolls horizontally instead of ever clipping,
            even after the row-level responsive sizing above */}
        <div className="overflow-x-auto rounded-2xl border border-[#E5E7EB] bg-white p-3 sm:p-4">
          <div className="min-w-[320px]">
            {loading ? (
              <div className="space-y-2 p-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full rounded-xl" />
                ))}
              </div>
            ) : filteredRoot ? (
              <OrgTreeRow
                node={filteredRoot}
                depth={0}
                isExpanded={isExpanded}
                onToggle={toggle}
                onAddChild={openAddChild}
                onEdit={openEdit}
                onMove={setMoveNode}
                onDelete={setDeleteNode}
              />
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-sm text-[#6B7280]">
                  {search ? "No nodes match your search." : "No organization structure yet."}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer legend */}
        <div className="mt-4 flex flex-col gap-4 rounded-2xl border border-[#E5E7EB] bg-white p-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-[#16A34A]">
            <Leaf className="h-4 w-4 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Building a sustainable future</p>
              <p className="text-xs text-[#9CA3AF]">Manage your organization with ESG in mind</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            {Object.entries(NODE_TYPE_CONFIG).map(([key, cfg]) => {
              const LegendIcon = cfg.icon;
              return (
                <div key={key} className="flex items-center gap-1.5 text-xs text-[#4B5563] sm:text-sm">
                  <div className={`flex h-5 w-5 items-center justify-center rounded-md sm:h-6 sm:w-6 ${cfg.iconBg}`}>
                    <LegendIcon className={`h-3 w-3 sm:h-3.5 sm:w-3.5 ${cfg.iconColor}`} />
                  </div>
                  {cfg.label}
                </div>
              );
            })}
          </div>
        </div>

        <OrgNodeFormPanel
          open={formState.open}
          mode={formState.mode}
          parentNode={formState.parentNode}
          editingNode={formState.editingNode}
          rootCompany={root?.company ?? ""}
          onClose={closeForm}
          onSaved={loadTree}
        />

        <OrgMoveDialog node={moveNode} root={root} onClose={() => setMoveNode(null)} onMoved={loadTree} />

        <ConfirmDialog
          open={deleteNode !== null}
          title="Delete Organization Node"
          description={`Are you sure you want to delete "${deleteNode?.name}"? This action cannot be undone.`}
          confirmText="Delete"
          loading={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteNode(null)}
        />
      </div>
    </AppShell>
  );
}