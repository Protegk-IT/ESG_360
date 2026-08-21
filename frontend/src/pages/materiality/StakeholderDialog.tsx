import {
  useState,
} from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  Input,
} from "@/components/ui/input";

import {
  Label,
} from "@/components/ui/label";

import {
  Button,
} from "@/components/ui/button";

import {
  UserPlus,
  Loader2,
} from "lucide-react";

import type {
  Stakeholder,
  StakeholderFormData,
} from "@/types/materiality/stakeholder";


interface StakeholderDialogProps {
  open: boolean;

  onClose: () => void;

  onSave: (
    data: StakeholderFormData
  ) => Promise<void>;

  groupId: string;

  groupName: string;

  saving?: boolean;

  stakeholder?: Stakeholder | null;
}


export default function StakeholderDialog({
  open,
  onClose,
  onSave,
  groupId,
  groupName,
  saving = false,
  stakeholder = null,
}: StakeholderDialogProps) {

  const [
    form,
    setForm,
  ] = useState<StakeholderFormData>({
    group: groupId,
    name: "",
    email: "",
    organisation: "",
    designation: "",
  });


  const [
    error,
    setError,
  ] = useState("");


  /* ========================================================
     INITIALIZE FORM
  ======================================================== */
/* ========================================================
   INITIALIZE FORM
   (reset happens during render, not in an effect, so it
   never triggers the "setState in effect" cascading-render
   warning — see https://react.dev/learn/you-might-not-need-an-effect)
======================================================== */

const [prevInitKey, setPrevInitKey] = useState({
  open,
  groupId,
  stakeholder,
});

if (
  open !== prevInitKey.open ||
  groupId !== prevInitKey.groupId ||
  stakeholder !== prevInitKey.stakeholder
) {
  setPrevInitKey({ open, groupId, stakeholder });

  if (open) {
    setError("");

    if (stakeholder) {
      setForm({
        group: stakeholder.group,
        name: stakeholder.name,
        email: stakeholder.email,
        organisation: stakeholder.organisation || "",
        designation: stakeholder.designation || "",
      });
    } else {
      setForm({
        group: groupId,
        name: "",
        email: "",
        organisation: "",
        designation: "",
      });
    }
  }
}


  /* ========================================================
     FIELD UPDATE
  ======================================================== */

  const updateField = (
    field: keyof StakeholderFormData,
    value: string
  ) => {

    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));

    setError("");
  };


  /* ========================================================
     SUBMIT
  ======================================================== */

  const handleSubmit = async (
    event: React.FormEvent
  ) => {

    event.preventDefault();

    if (!form.name.trim()) {
      setError(
        "Stakeholder name is required."
      );
      return;
    }

    if (!form.email.trim()) {
      setError(
        "Stakeholder email is required."
      );
      return;
    }

    if (!form.group) {
      setError(
        "Stakeholder group is required."
      );
      return;
    }

    try {

      await onSave({
        ...form,
        name: form.name.trim(),
        email: form.email.trim(),
        organisation:
          form.organisation.trim(),
        designation:
          form.designation.trim(),
      });

    } catch (err) {

      console.error(
        "Failed to save stakeholder:",
        err
      );

      setError(
        "Unable to save stakeholder. Please try again."
      );
    }
  };


  /* ========================================================
     RENDER
  ======================================================== */

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {

        if (!value && !saving) {
          onClose();
        }

      }}
    >

      <DialogContent
        className="
          max-w-lg
          rounded-xl
          border
          border-slate-200
          bg-white
          p-0
          shadow-xl
        "
      >

        {/* ==================================================
            HEADER
        ================================================== */}

        <DialogHeader
          className="
            border-b
            border-slate-200
            px-6
            py-5
          "
        >

          <div
            className="
              flex
              items-center
              gap-3
            "
          >

            <div
              className="
                flex
                h-9
                w-9
                items-center
                justify-center
                rounded-lg
                bg-emerald-50
                text-emerald-600
              "
            >

              <UserPlus
                className="
                  h-4
                  w-4
                "
              />

            </div>

            <div>

              <DialogTitle
                className="
                  text-base
                  font-semibold
                  text-slate-900
                "
              >
                {stakeholder
                  ? "Edit Stakeholder"
                  : "Add Stakeholder"}
              </DialogTitle>

              <DialogDescription
                className="
                  mt-1
                  text-xs
                  text-slate-500
                "
              >
                Add an individual stakeholder
                to{" "}
                <span
                  className="
                    font-medium
                    text-slate-700
                  "
                >
                  {groupName}
                </span>
                .
              </DialogDescription>

            </div>

          </div>

        </DialogHeader>


        {/* ==================================================
            FORM
        ================================================== */}

        <form
          onSubmit={handleSubmit}
          className="
            space-y-5
            px-6
            py-5
          "
        >

          {/* =================================================
              NAME
          ================================================= */}

          <div
            className="
              space-y-2
            "
          >

            <Label
              htmlFor="stakeholder-name"
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Name
              <span
                className="
                  ml-1
                  text-red-500
                "
              >
                *
              </span>
            </Label>

            <Input
              id="stakeholder-name"
              value={form.name}
              disabled={saving}
              placeholder="Enter stakeholder name"
              onChange={(event) =>
                updateField(
                  "name",
                  event.target.value
                )
              }
            />

          </div>


          {/* =================================================
              EMAIL
          ================================================= */}

          <div
            className="
              space-y-2
            "
          >

            <Label
              htmlFor="stakeholder-email"
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Email
              <span
                className="
                  ml-1
                  text-red-500
                "
              >
                *
              </span>
            </Label>

            <Input
              id="stakeholder-email"
              type="email"
              value={form.email}
              disabled={saving}
              placeholder="name@example.com"
              onChange={(event) =>
                updateField(
                  "email",
                  event.target.value
                )
              }
            />

          </div>


          {/* =================================================
              ORGANISATION
          ================================================= */}

          <div
            className="
              space-y-2
            "
          >

            <Label
              htmlFor="stakeholder-organisation"
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Organisation
            </Label>

            <Input
              id="stakeholder-organisation"
              value={form.organisation}
              disabled={saving}
              placeholder="Enter organisation"
              onChange={(event) =>
                updateField(
                  "organisation",
                  event.target.value
                )
              }
            />

          </div>


          {/* =================================================
              DESIGNATION
          ================================================= */}

          <div
            className="
              space-y-2
            "
          >

            <Label
              htmlFor="stakeholder-designation"
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Designation
            </Label>

            <Input
              id="stakeholder-designation"
              value={form.designation}
              disabled={saving}
              placeholder="Enter designation"
              onChange={(event) =>
                updateField(
                  "designation",
                  event.target.value
                )
              }
            />

          </div>


          {/* =================================================
              ERROR
          ================================================= */}

          {error && (
            <div
              className="
                rounded-lg
                border
                border-red-200
                bg-red-50
                px-3
                py-2
                text-xs
                text-red-700
              "
            >
              {error}
            </div>
          )}


          {/* =================================================
              FOOTER
          ================================================= */}

          <DialogFooter
            className="
              gap-2
              border-t
              border-slate-100
              pt-5
            "
          >

            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={onClose}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              disabled={saving}
              className="
                bg-emerald-600
                text-white
                hover:bg-emerald-700
              "
            >

              {saving && (
                <Loader2
                  className="
                    mr-2
                    h-4
                    w-4
                    animate-spin
                  "
                />
              )}

              {stakeholder
                ? "Save Changes"
                : "Add Stakeholder"}

            </Button>

          </DialogFooter>

        </form>

      </DialogContent>

    </Dialog>
  );
}