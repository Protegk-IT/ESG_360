import { useMemo, useState } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import OrganizationApi from "@/api/organizations/OrganizationApi";
import type { OrgNode } from "@/types/organization";

interface OrgMoveDialogProps {
  node: OrgNode | null;
  root: OrgNode | null;
  onClose: () => void;
  onMoved: () => void;
}

// Excludes the node itself and its whole subtree — a node can't be
// reparented under one of its own descendants.
function flattenValidParents(
  node: OrgNode,
  excludeId: string,
  path = ""
): { id: string; label: string }[] {
  if (node.id === excludeId) return [];

  const label = `${path}${node.name}`;
  const childResults = (node.children ?? []).flatMap((c) =>
    flattenValidParents(c, excludeId, `${label} / `)
  );

  return [{ id: node.id, label }, ...childResults];
}

export default function OrgMoveDialog({ node, root, onClose, onMoved }: OrgMoveDialogProps) {
  const [targetParent, setTargetParent] = useState<string>("");
  const [saving, setSaving] = useState(false);

  const options = useMemo(() => {
    if (!root || !node) return [];
    return flattenValidParents(root, node.id);
  }, [root, node]);

  if (!node) return null;

  const handleMove = async () => {
    try {
      setSaving(true);
      await OrganizationApi.move(node.id, targetParent || null);
      toast.success(`${node.name} moved successfully.`);
      onMoved();
      onClose();
    } catch (error) {
      console.error(error);
      toast.error("Unable to move node. Check that the target doesn't create a cycle.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={node !== null} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Move &quot;{node.name}&quot;</DialogTitle>
        </DialogHeader>

        <div className="space-y-1.5 py-2">
          <Select value={targetParent} onValueChange={setTargetParent}>
            <SelectTrigger>
              <SelectValue placeholder="Select new parent" />
            </SelectTrigger>
            <SelectContent>
              {options.map((opt) => (
                <SelectItem key={opt.id} value={opt.id}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleMove} disabled={saving || !targetParent}>
            {saving ? "Moving..." : "Move"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}