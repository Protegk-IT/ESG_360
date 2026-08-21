import {
  useEffect,
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
import { Checkbox } from "@/components/ui/checkbox";

import {
  Input,
} from "@/components/ui/input";

import {
  Label,
} from "@/components/ui/label";

import {
  Textarea,
} from "@/components/ui/textarea";


import {
  Button,
} from "@/components/ui/button";

import {
  Badge,
} from "@/components/ui/badge";

import {
  Loader2,
} from "lucide-react";

import type {
  StakeholderGroup,
  StakeholderGroupFormData,
} from "@/types/materiality/stakeholder";


/* ==========================================================
   PROPS
========================================================== */

interface StakeholderGroupDialogProps {
  open: boolean;

  onClose: () => void;

  onSave: (
    data: StakeholderGroupFormData
  ) => Promise<void>;

  group?: StakeholderGroup | null;

  currentTotalWeight: number;
  saving: boolean;
}


/* ==========================================================
   DEFAULT FORM
========================================================== */

const DEFAULT_FORM: StakeholderGroupFormData = {
  name: "",
  description: "",
  weight: "",
  is_internal: false,
};


/* ==========================================================
   COMPONENT
========================================================== */

export default function StakeholderGroupDialog({
  open,
  onClose,
  onSave,
  group,
  currentTotalWeight,
}: StakeholderGroupDialogProps) {

  const isEditMode = Boolean(group);

  const [
    form,
    setForm,
  ] = useState<StakeholderGroupFormData>(
    DEFAULT_FORM
  );

  const [
    error,
    setError,
  ] = useState<string | null>(null);

  const [
    saving,
    setSaving,
  ] = useState(false);


  /* ========================================================
     RESET / LOAD FORM
  ======================================================== */

  useEffect(() => {
  if (!open) {
    return;
  }

  const timer = setTimeout(() => {
    if (group) {
      setForm({
        name: group.name,
        description: group.description ?? "",
        weight: String(group.weight),
        is_internal: group.is_internal,
      });
    } else {
      setForm(DEFAULT_FORM);
    }

    setError(null);
  }, 0);

  return () => clearTimeout(timer);
}, [open, group]);

  /* ========================================================
     CURRENT GROUP WEIGHT
     
     When editing, remove the existing group's weight
     from the total before calculating the maximum.
  ======================================================== */

  const existingGroupWeight =
    group
      ? Number(group.weight)
      : 0;


  const totalWithoutCurrentGroup =
    currentTotalWeight -
    existingGroupWeight;


  const remainingWeight = Math.max(
    0,
    100 - totalWithoutCurrentGroup
  );


  /* ========================================================
     FIELD UPDATE
  ======================================================== */

  const updateField = <
    K extends keyof StakeholderGroupFormData
  >(
    field: K,
    value: StakeholderGroupFormData[K]
  ) => {

    setForm(
      (previous) => ({
        ...previous,
        [field]: value,
      })
    );

    if (error) {
      setError(null);
    }
  };


  /* ========================================================
     SAVE
  ======================================================== */

  const handleSave = async () => {

    /* ------------------------------------------------------
       NAME
    ------------------------------------------------------ */

    if (!form.name.trim()) {

      setError(
        "Stakeholder group name is required."
      );

      return;
    }


    /* ------------------------------------------------------
       WEIGHT
    ------------------------------------------------------ */

    if (!form.weight.trim()) {

      setError(
        "Weight is required."
      );

      return;
    }


    const weight =
      Number(form.weight);


    if (!Number.isFinite(weight)) {

      setError(
        "Weight must be a valid number."
      );

      return;
    }


    if (weight < 0) {

      setError(
        "Weight cannot be negative."
      );

      return;
    }


    if (weight > 100) {

      setError(
        "Weight cannot be greater than 100%."
      );

      return;
    }


    /* ------------------------------------------------------
       TOTAL WEIGHT
    ------------------------------------------------------ */

    const newTotal =
      totalWithoutCurrentGroup +
      weight;


    if (newTotal > 100) {

      setError(
        `Weight cannot exceed the remaining ${remainingWeight.toFixed(
          2
        )}%.`
      );

      return;
    }


    /* ------------------------------------------------------
       API DATA
    ------------------------------------------------------ */

    const data: StakeholderGroupFormData = {
      name: form.name.trim(),

      description:
        form.description.trim(),

      weight:
        weight.toFixed(2),

      is_internal:
        form.is_internal,
    };


    /* ------------------------------------------------------
       SAVE
    ------------------------------------------------------ */

    try {

      setSaving(true);

      setError(null);

      await onSave(data);

      onClose();

    } catch (err: unknown) {

      console.error(
        "Failed to save stakeholder group:",
        err
      );

      setError(
        "Unable to save stakeholder group. Please try again."
      );

    } finally {

      setSaving(false);

    }
  };


  /* ========================================================
     CANCEL
  ======================================================== */

  const handleClose = () => {

    if (saving) {
      return;
    }

    setError(null);

    onClose();
  };


  /* ========================================================
     UI
  ======================================================== */

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {

        if (!value) {
          handleClose();
        }

      }}
    >

      <DialogContent
        className="
          max-w-lg
          border-slate-200
          bg-white
          shadow-xl
        "
      >

        {/* ==================================================
            HEADER
        ================================================== */}

        <DialogHeader>

          <DialogTitle
            className="
              text-xl
              font-semibold
              text-slate-900
            "
          >
            {isEditMode
              ? "Edit Stakeholder Group"
              : "Add Stakeholder Group"}
          </DialogTitle>

          <DialogDescription
            className="
              text-sm
              text-slate-500
            "
          >
            {isEditMode
              ? "Update the stakeholder group configuration."
              : "Create a stakeholder group for this materiality assessment."}
          </DialogDescription>

        </DialogHeader>


        {/* ==================================================
            FORM
        ================================================== */}

        <div className="space-y-5 py-2">

          {/* =================================================
              NAME
          ================================================= */}

          <div className="space-y-2">

            <Label
              htmlFor="stakeholder-group-name"
              className="text-slate-700"
            >
              Group Name
              <span className="ml-1 text-red-500">
                *
              </span>
            </Label>

            <Input
              id="stakeholder-group-name"
              placeholder="e.g. Employees"
              value={form.name}
              disabled={saving}
              onChange={(event) =>
                updateField(
                  "name",
                  event.target.value
                )
              }
              className="
                border-slate-200
                focus-visible:ring-1
              "
            />

          </div>


          {/* =================================================
              DESCRIPTION
          ================================================= */}

          <div className="space-y-2">

            <Label
              htmlFor="stakeholder-group-description"
              className="text-slate-700"
            >
              Description
            </Label>

            <Textarea
              id="stakeholder-group-description"
              placeholder="Describe this stakeholder group..."
              value={form.description}
              disabled={saving}
              rows={3}
              onChange={(event) =>
                updateField(
                  "description",
                  event.target.value
                )
              }
              className="
                resize-none
                border-slate-200
                focus-visible:ring-1
              "
            />

          </div>


          {/* =================================================
              WEIGHT
          ================================================= */}

          <div className="space-y-2">

            <div className="flex items-center justify-between">

              <Label
                htmlFor="stakeholder-group-weight"
                className="text-slate-700"
              >
                Weight
                <span className="ml-1 text-red-500">
                  *
                </span>
              </Label>

              <Badge
                variant="outline"
                className="
                  border-slate-200
                  bg-slate-50
                  text-slate-600
                "
              >
                Remaining:{" "}
                {remainingWeight.toFixed(2)}%
              </Badge>

            </div>

            <div className="relative">

              <Input
                id="stakeholder-group-weight"
                type="number"
                min={0}
                max={remainingWeight}
                step="0.01"
                placeholder="0.00"
                value={form.weight}
                disabled={saving}
                onChange={(event) =>
                  updateField(
                    "weight",
                    event.target.value
                  )
                }
                className="
                  border-slate-200
                  pr-10
                  focus-visible:ring-1
                "
              />

              <span
                className="
                  pointer-events-none
                  absolute
                  right-3
                  top-1/2
                  -translate-y-1/2
                  text-sm
                  text-slate-400
                "
              >
                %
              </span>

            </div>

            <p className="text-xs text-slate-500">
              The total weight of all stakeholder
              groups cannot exceed 100%.
            </p>

          </div>


          {/* =================================================
              INTERNAL / EXTERNAL
          ================================================= */}
<div
  className="
    flex
    items-center
    justify-between
    rounded-lg
    border
    border-slate-200
    bg-slate-50
    px-4
    py-3
  "
>
  <div>
    <p
      className="
        text-sm
        font-medium
        text-slate-800
      "
    >
      Internal Stakeholder Group
    </p>

    <p
      className="
        mt-0.5
        text-xs
        text-slate-500
      "
    >
      Mark this group as internal to
      the organisation.
    </p>
  </div>

  <Checkbox
    checked={form.is_internal}
    disabled={saving}
    onCheckedChange={(checked) =>
      updateField(
        "is_internal",
        checked === true
      )
    }
  />
</div>
          {/* =================================================
              VALIDATION ERROR
          ================================================= */}

          {error && (

            <div
              className="
                rounded-lg
                border
                border-red-200
                bg-red-50
                px-4
                py-3
                text-sm
                text-red-700
              "
            >
              {error}
            </div>

          )}

        </div>


        {/* ==================================================
            FOOTER
        ================================================== */}

        <DialogFooter>

          <Button
            type="button"
            variant="outline"
            disabled={saving}
            onClick={handleClose}
          >
            Cancel
          </Button>

          <Button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="
              bg-slate-900
              text-white
              hover:bg-slate-800
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

            {isEditMode
              ? "Save Changes"
              : "Add Group"}

          </Button>

        </DialogFooter>

      </DialogContent>

    </Dialog>
  );
}