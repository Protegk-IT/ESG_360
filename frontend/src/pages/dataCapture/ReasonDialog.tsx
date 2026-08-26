import { useState,useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface ReasonDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmText: string;
  loading?: boolean;
  destructive?: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export default function ReasonDialog({
  open,
  title,
  description,
  confirmText,
  loading,
  destructive,
  onConfirm,
  onCancel,
}: ReasonDialogProps) {
  const [reason, setReason] = useState("");
  const trimmed = reason.trim();
 useEffect(() => {
  if (!open) {
    return;
  }

  let ignore = false;

  Promise.resolve().then(() => {
    if (!ignore) {
      setReason("");
    }
  });

  return () => {
    ignore = true;
  };
}, [open]); 

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !loading) {
          setReason("");
          onCancel();
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <Textarea
          autoFocus
          rows={4}
          placeholder="Provide a reason..."
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          disabled={loading}
          className="resize-y"
        />

        {trimmed.length === 0 && (
          <p className="text-xs text-muted-foreground">
            A reason is required to continue.
          </p>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setReason("");
              onCancel();
            }}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant={destructive ? "destructive" : "default"}
            disabled={loading || trimmed.length === 0}
            onClick={() => onConfirm(trimmed)}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}