import {
  useEffect,
  useState,
} from "react";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import axios from "axios";
import { toast } from "sonner";
import { Slider } from "@/components/ui/slider";

import type {
  AssessmentMode,
  MaterialityAssessmentFormData,
} from "@/types/materiality/assessment";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

import {
  Input,
} from "@/components/ui/input";

import {
  Label,
} from "@/components/ui/label";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Button,
} from "@/components/ui/button";
import type { ReportingPeriod } from "@/types/reporting-period";


/* ==========================================================
   PROPS
========================================================== */

interface AssessmentCreateDialogProps {
  open: boolean;

  onClose: () => void;

  onSaved: () => void;
}


/* ==========================================================
   EMPTY FORM
========================================================== */

const emptyForm: MaterialityAssessmentFormData = {
  name: "",
  reporting_period: "",
  mode: "DOUBLE",
  primary_threshold: 3,
  secondary_threshold: 3,
};


/* ==========================================================
   COMPONENT

   NOTE ON RESETTING FORM STATE:

   This dialog no longer resets its form inside a
   useEffect keyed on `open`. Calling setState synchronously
   inside an effect body just to sync local state to a prop
   is the exact anti-pattern React's docs warn about — it
   causes an extra render pass every time the dialog opens.

   Instead, the parent (AssessmentList) renders this
   component with `key={open ? "open" : "closed"}`. Changing
   the key remounts this component fresh whenever it opens,
   so `useState(emptyForm)` below IS the reset — no effect
   required. See: https://react.dev/learn/you-might-not-need-an-effect
========================================================== */

export default function AssessmentCreateDialog({
  open,
  onClose,
  onSaved,
}: AssessmentCreateDialogProps) {

// Reporting Period

const [reportingPeriods, setReportingPeriods] = useState<
  ReportingPeriod[]
>([]);

const [loadingPeriods, setLoadingPeriods] = useState(false);


useEffect(() => {
  if (!open) return;

  const loadReportingPeriods = async () => {
    try {
      setLoadingPeriods(true);

      const data =
        await AssessmentApi.getReportingPeriods();

      setReportingPeriods(data);

    } catch (error) {
      console.error(
        "Failed to load reporting periods:",
        error
      );

      toast.error(
        "Failed to load reporting periods."
      );

    } finally {
      setLoadingPeriods(false);
    }
  };

  loadReportingPeriods();

}, [open]);

  /* ========================================================
     FORM STATE
  ======================================================== */

  const [
    form,
    setForm,
  ] = useState<MaterialityAssessmentFormData>(
    emptyForm
  );


  /* ========================================================
     UI STATE
  ======================================================== */

  const [
    saving,
    setSaving,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  /* ========================================================
     UPDATE FIELD
  ======================================================== */

  const update = <
    K extends keyof MaterialityAssessmentFormData
  >(
    field: K,
    value: MaterialityAssessmentFormData[K]
  ) => {

    setForm(
      (previous) => ({
        ...previous,
        [field]: value,
      })
    );

    setError(null);

  };


  /* ========================================================
     SAVE
  ======================================================== */

const handleSave = async () => {
  /* ------------------------------------------------------
     BASIC VALIDATION
  ------------------------------------------------------ */

  if (!form.name.trim()) {
    setError("Assessment name is required.");
    return;
  }

  if (!form.reporting_period.trim()) {
    setError("Reporting period  is required.");
    return;
  }




  /* ------------------------------------------------------
     API REQUEST
  ------------------------------------------------------ */

  try {
    setSaving(true);
    setError(null);

    await AssessmentApi.create({
      name: form.name.trim(),
      reporting_period: form.reporting_period.trim(),
      mode: form.mode,
      primary_threshold: form.primary_threshold,
      secondary_threshold: form.secondary_threshold,
    });

    /* ----------------------------------------------------
       SUCCESS TOAST
    ---------------------------------------------------- */

    toast.success(
      "Assessment created successfully.",
      {
        description:
          `${form.name.trim()} has been added successfully.`,
      }
    );

    /* ----------------------------------------------------
       REFRESH LIST
    ---------------------------------------------------- */

    onSaved();

    /* ----------------------------------------------------
       CLOSE DIALOG
    ---------------------------------------------------- */

    onClose();

  } catch (err: unknown) {
    console.error(
      "Failed to create assessment:",
      err
    );

    let errorMessage =
      "Unable to create assessment. Please try again.";

    /* ----------------------------------------------------
       AXIOS / DRF VALIDATION ERROR
    ---------------------------------------------------- */

    if (axios.isAxiosError(err)) {
      const responseData =
        err.response?.data;

      if (
        responseData &&
        typeof responseData === "object"
      ) {
        const firstError =
          Object.values(responseData)[0];

        if (Array.isArray(firstError)) {
          errorMessage =
            String(firstError[0]);
        } else if (
          typeof firstError === "string"
        ) {
          errorMessage =
            firstError;
        }
      }
    }

    setError(errorMessage);

    /* ----------------------------------------------------
       ERROR TOAST
    ---------------------------------------------------- */

    toast.error(
      "Failed to create assessment.",
      {
        description: errorMessage,
      }
    );

  } finally {
    setSaving(false);
  }
};
  /* ========================================================
     UI
  ======================================================== */

  return (

    <Dialog
      open={open}
      onOpenChange={(next) => {

        if (!next && !saving) {
          onClose();
        }

      }}
    >

      <DialogContent
        className="
          max-h-[85vh]
          overflow-y-auto
          bg-white
          shadow-2xl
          sm:max-w-lg
        "
      >

        {/* ==================================================
            HEADER
        ================================================== */}

        <DialogHeader>

          <DialogTitle>
            Create Materiality Assessment
          </DialogTitle>

          <DialogDescription>
            Create an assessment and choose
            the materiality approach you want
            to use.
          </DialogDescription>

        </DialogHeader>


        {/* ==================================================
            FORM CONTENT
        ================================================== */}

        <div
          className="
            space-y-5
            py-3
          "
        >

          {/* ==================================================
              ERROR
          ================================================== */}

          {error && (

            <div
              className="
                rounded-lg
                border
                border-red-200
                bg-red-50
                px-3
                py-2.5
                text-sm
                text-red-700
              "
            >
              {error}
            </div>

          )}


          {/* ==================================================
              BASIC DETAILS
          ================================================== */}

          <div
            className="
              space-y-3
              rounded-lg
              border
              border-[#E5E7EB]
              bg-white
              p-4
            "
          >

            <div>

              <p
                className="
                  text-xs
                  font-semibold
                  uppercase
                  tracking-wide
                  text-[#6B7280]
                "
              >
                Assessment Details
              </p>

              <p
                className="
                  mt-1
                  text-xs
                  text-slate-500
                "
              >
                Define the basic information
                for this materiality assessment.
              </p>

            </div>


            {/* ==================================================
                NAME
            ================================================== */}

            <div className="space-y-1.5">

              <Label htmlFor="assessment-name">
                Assessment Name
              </Label>

              <Input
                id="assessment-name"
                value={form.name}
                onChange={(event) =>
                  update(
                    "name",
                    event.target.value
                  )
                }
                placeholder="
                  e.g. FY 2026-27 Materiality Assessment
                "
                disabled={saving}
              />

            </div>


            {/* ==================================================
                FINANCIAL YEAR
            ================================================== */}

          {/* ==================================================
    REPORTING PERIOD
================================================== */}

<div className="space-y-1.5">

  <Label>
    Reporting Period
  </Label>

  <Select
    value={form.reporting_period}
    onValueChange={(value) =>
      update(
        "reporting_period",
        value
      )
    }
    disabled={
      saving ||
      loadingPeriods
    }
  >

    <SelectTrigger>
      <SelectValue
        placeholder={
          loadingPeriods
            ? "Loading reporting periods..."
            : "Select reporting period"
        }
      />
    </SelectTrigger>

    <SelectContent>

      {reportingPeriods.map(
        (period) => (
          <SelectItem
            key={period.id}
            value={period.id}
          >
            {period.name}
            {" "}
            (
            {period.start_date}
            {" → "}
            {period.end_date}
            )
          </SelectItem>
        )
      )}

    </SelectContent>

  </Select>

</div>
</div>


          {/* ==================================================
              MATERIALITY MODE
          ================================================== */}

          <div
            className="
              space-y-3
              rounded-lg
              border
              border-[#E5E7EB]
              bg-white
              p-4
            "
          >

            <div>

              <p
                className="
                  text-xs
                  font-semibold
                  uppercase
                  tracking-wide
                  text-[#6B7280]
                "
              >
                Materiality Approach
              </p>

              <p
                className="
                  mt-1
                  text-xs
                  text-slate-500
                "
              >
                Select how materiality will be
                assessed for this assessment.
              </p>

            </div>


            {/* ==================================================
                MODE SELECT
            ================================================== */}

            <div className="space-y-1.5">

              <Label>
                Materiality Mode
              </Label>

              <Select
                value={form.mode}
                onValueChange={(value) =>
                  update(
                    "mode",
                    value as AssessmentMode
                  )
                }
                disabled={saving}
              >

                <SelectTrigger>

                  <SelectValue />

                </SelectTrigger>

                <SelectContent>

                  <SelectItem
                    value="SINGLE"
                  >
                    Single Materiality
                  </SelectItem>

                  <SelectItem
                    value="DOUBLE"
                  >
                    Double Materiality
                  </SelectItem>

                </SelectContent>

              </Select>

            </div>


          </div>

        </div>


     
{/* ==================================================
    MATERIALITY THRESHOLDS
================================================== */}

<div className="space-y-6">

  {/* PRIMARY THRESHOLD */}
  <div className="mx-auto w-full max-w-[320px] space-y-2">
    <div className="flex items-center justify-between">
      <Label className="text-sm font-semibold text-foreground">
        Primary Threshold
      </Label>

      <span className="text-sm font-semibold text-blue-600">
        {Number(form.primary_threshold).toFixed(1)}
      </span>
    </div>

    <p className="text-xs text-muted-foreground">
      Minimum score required for primary materiality.
    </p>

    <div className="pt-2">
      <Slider
        value={[form.primary_threshold]}
        min={1}
        max={5}
        step={0.1}
        onValueChange={(value) =>
          update("primary_threshold", value[0])
        }
        disabled={saving}
        className="w-full"
      />
    </div>

    <div className="flex justify-between px-1 text-[11px] text-muted-foreground">
      <span>1</span>
      <span>2</span>
      <span>3</span>
      <span>4</span>
      <span>5</span>
    </div>
  </div>


  {/* SECONDARY THRESHOLD */}
  {form.mode === "DOUBLE" && (
    <div className="mx-auto w-full max-w-[320px] space-y-2">

      <div className="flex items-center justify-between">
        <Label className="text-sm font-semibold text-foreground">
          Secondary Threshold
        </Label>

        <span className="text-sm font-semibold text-blue-600">
          {Number(form.secondary_threshold).toFixed(1)}
        </span>
      </div>

      <p className="text-xs text-muted-foreground">
        Minimum score required for secondary materiality.
      </p>

      <div className="pt-2">
        <Slider
          value={[form.secondary_threshold]}
          min={1}
          max={5}
          step={0.1}
          onValueChange={(value) =>
            update("secondary_threshold", value[0])
          }
          disabled={saving}
          className="w-full"
        />
      </div>

      <div className="flex justify-between px-1 text-[11px] text-muted-foreground">
        <span>1</span>
        <span>2</span>
        <span>3</span>
        <span>4</span>
        <span>5</span>
      </div>

    </div>
  )}

</div>
        {/* ==================================================
            FOOTER
        ================================================== */}

        <DialogFooter>

          <Button
            variant="outline"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </Button>

          <Button
            onClick={handleSave}
            disabled={saving}
            className="
              bg-[#4A3FD6]
              hover:bg-[#4036C0]
            "
          >
            {saving
              ? "Creating..."
              : "Create Assessment"}
          </Button>

        </DialogFooter>

      </DialogContent>

    </Dialog>

  );
}