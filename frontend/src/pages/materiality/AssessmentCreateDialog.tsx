import {
  useState,
} from "react";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import axios from "axios";

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
  financial_year: "",
  period_start: "",
  period_end: "",
  mode: "DOUBLE",
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

    if (!form.financial_year.trim()) {
      setError("Financial year is required.");
      return;
    }

    if (!form.period_start) {
      setError("Period start date is required.");
      return;
    }

    if (!form.period_end) {
      setError("Period end date is required.");
      return;
    }

    if (form.period_start > form.period_end) {
      setError(
        "Period end date must be greater than or equal to the period start date."
      );
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
        financial_year: form.financial_year.trim(),
        period_start: form.period_start,
        period_end: form.period_end,
        mode: form.mode,
      });

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

      /* ----------------------------------------------------
         AXIOS / DRF VALIDATION ERROR
      ---------------------------------------------------- */

      if (axios.isAxiosError(err)) {
        const responseData = err.response?.data;

        if (
          responseData &&
          typeof responseData === "object"
        ) {
          const firstError = Object.values(
            responseData
          )[0];

          if (Array.isArray(firstError)) {
            setError(String(firstError[0]));
          } else if (
            typeof firstError === "string"
          ) {
            setError(firstError);
          } else {
            setError(
              "Unable to create assessment."
            );
          }
        } else {
          setError(
            "Unable to create assessment. Please try again."
          );
        }
      } else {
        /* --------------------------------------------------
           NON-AXIOS / UNKNOWN ERROR
        -------------------------------------------------- */

        setError(
          "Unable to create assessment. Please try again."
        );
      }
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

            <div className="space-y-1.5">

              <Label htmlFor="financial-year">
                Financial Year
              </Label>

              <Input
                id="financial-year"
                value={
                  form.financial_year
                }
                onChange={(event) =>
                  update(
                    "financial_year",
                    event.target.value
                  )
                }
                placeholder="e.g. FY 2026-27"
                disabled={saving}
              />

            </div>


            {/* ==================================================
                PERIOD
            ================================================== */}

            <div
              className="
                grid
                grid-cols-1
                gap-3
                sm:grid-cols-2
              "
            >

              <div className="space-y-1.5">

                <Label htmlFor="period-start">
                  Period Start
                </Label>

                <Input
                  id="period-start"
                  type="date"
                  value={
                    form.period_start
                  }
                  onChange={(event) =>
                    update(
                      "period_start",
                      event.target.value
                    )
                  }
                  disabled={saving}
                />

              </div>


              <div className="space-y-1.5">

                <Label htmlFor="period-end">
                  Period End
                </Label>

                <Input
                  id="period-end"
                  type="date"
                  value={
                    form.period_end
                  }
                  onChange={(event) =>
                    update(
                      "period_end",
                      event.target.value
                    )
                  }
                  disabled={saving}
                />

              </div>

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
                    value="IMPACT"
                  >
                    Impact Materiality
                  </SelectItem>
                   <SelectItem
                    value="FINANCIAL"
                  >
                    Financial Materiality
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