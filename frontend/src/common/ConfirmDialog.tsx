import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  loading?: boolean;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmText = "Delete",
  cancelText = "Cancel",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <AlertDialog
      open={open}
      onOpenChange={(value) => {
        if (!value) onCancel();
      }}
    >
      <AlertDialogContent
        className="
          max-w-md

          overflow-hidden

          rounded-xl

          border
          border-[#D9DEE8]

          bg-white

          p-0

          shadow-2xl
        "
      >
        {/* Header */}

        <AlertDialogHeader
          className="
            px-6
            py-6
            text-left
          "
        >
          <div className="flex items-start gap-4">

            <div
              className="
                flex
                h-12
                w-12
                items-center
                justify-center

                rounded-xl

                border
                border-[#E8D3D2]

                bg-[#F6ECEB]
              "
            >
              <AlertTriangle
                className="
                  h-6
                  w-6
                  text-[#B3453F]
                "
              />
            </div>

            <div className="space-y-2">

              <AlertDialogTitle
                className="
                  text-lg
                  font-semibold
                  tracking-tight
                  text-[#111827]
                "
              >
                {title}
              </AlertDialogTitle>

              <AlertDialogDescription
                className="
                  text-sm
                  leading-6
                  text-[#6B7280]
                "
              >
                {description}
              </AlertDialogDescription>

            </div>

          </div>
        </AlertDialogHeader>

        {/* Footer */}

        <AlertDialogFooter
          className="
            border-t
            border-[#ECEEF5]

            bg-[#FAFAFC]

            px-6
            py-4

            sm:flex-row
            sm:justify-end
            sm:gap-3
          "
        >
          <AlertDialogCancel
            className="
              min-w-[100px]
            "
          >
            {cancelText}
          </AlertDialogCancel>

          <AlertDialogAction
            disabled={loading}
            onClick={onConfirm}
            className="
              min-w-[110px]

              bg-[#B3453F]

              hover:bg-[#9C3B36]
            "
          >
            {loading
              ? "Deleting..."
              : confirmText}
          </AlertDialogAction>

        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}