import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AxiosError } from "axios";
import { toast } from "sonner";
import AppShell from "@/components/layout/AppShell";
import ReportingPeriodApi from "@/api/reporting_periods/ReportingPeriodApi";
import type {
  ReportingPeriod,
  ReportingPeriodFormData,
} from "@/types/reporting-period";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ValidationErrors {
  [key: string]: string[];
}

const emptyForm: ReportingPeriodFormData = {
  parent: null,
  name: "",
  period_type: "ANNUAL",
  start_date: "",
  end_date: "",
  status: "OPEN",
  is_baseline_year: false,
  is_active: true,
};

export default function ReportingPeriodForm() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);

  /* ==========================================================
      STATE
  ========================================================== */

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<ReportingPeriodFormData>(emptyForm);
  const [parentPeriods, setParentPeriods] = useState<ReportingPeriod[]>([]);

  /* ==========================================================
      FIELD UPDATE
  ========================================================== */

  function updateField<K extends keyof ReportingPeriodFormData>(
    field: K,
    value: ReportingPeriodFormData[K]
  ) {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  /* ==========================================================
      LOAD DATA
      React 19 Safe
  ========================================================== */

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        setLoading(true);

        const parentResponse = await ReportingPeriodApi.getAll();
        if (cancelled) return;
        setParentPeriods(parentResponse.data);

        if (isEdit && id) {
          const response = await ReportingPeriodApi.getById(id);
          if (cancelled) return;

          const period = response.data;

          setFormData({
            parent: period.parent,
            name: period.name,
            period_type: period.period_type,
            start_date: period.start_date,
            end_date: period.end_date,
            status: period.status,
            is_baseline_year: period.is_baseline_year,
            is_active: period.is_active,
          });
        }
      } catch (error) {
        console.error(error);
        if (!cancelled) {
          toast.error("Unable to load reporting period.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchData();

    return () => {
      cancelled = true;
    };
  }, [id, isEdit]);

  /* ==========================================================
      SUBMIT
  ========================================================== */

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    try {
      setSaving(true);

      if (isEdit && id) {
        await ReportingPeriodApi.update(id, formData);
        toast.success("Reporting period updated successfully.");
      } else {
        await ReportingPeriodApi.create(formData);
        toast.success("Reporting period created successfully.");
      }

      navigate("/periods");
    } catch (error: unknown) {
      const axiosError = error as AxiosError<ValidationErrors>;

      if (axiosError.response?.data) {
        Object.entries(axiosError.response.data).forEach(([field, messages]) => {
          toast.error(`${field}: ${messages.join(", ")}`);
        });
      } else {
        toast.error("Something went wrong.");
      }
    } finally {
      setSaving(false);
    }
  }

  /* ==========================================================
      UI
  ========================================================== */

  return (
    <AppShell
      title={isEdit ? "Edit Reporting Period" : "Create Reporting Period"}
      description={
        isEdit
          ? "Update reporting period information."
          : "Create a reporting period for ESG reporting."
      }
    >
      <form
        onSubmit={handleSubmit}
        className="mx-auto w-full max-w-4xl space-y-6 px-4 sm:px-0"
      >
        {/* ======================================================
            REPORTING PERIOD DETAILS — single card
        ====================================================== */}

        <Card className="border border-[#E5E7EB] bg-white">
          <CardHeader className="p-5 pb-4 sm:p-6 sm:pb-4">
            <CardTitle>Reporting Period Details</CardTitle>
            <CardDescription>
              Configure the period details and reporting settings.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-8 p-5 pt-0 sm:p-6 sm:pt-0">
            {/* ---------------- General Information ---------------- */}
            <div className="space-y-5">
              <h3 className="text-sm font-semibold text-[#111827]">
                General Information
              </h3>

              <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
                {/* Period Name */}
                <div className="space-y-2">
                  <Label>Period Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => updateField("name", e.target.value)}
                    placeholder="FY 2025-26"
                  />
                </div>

                {/* Type */}
                <div className="space-y-2">
                  <Label>Period Type</Label>
                  <Select
                    value={formData.period_type}
                    onValueChange={(value) =>
                      updateField(
                        "period_type",
                        value as ReportingPeriodFormData["period_type"]
                      )
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ANNUAL">Annual</SelectItem>
                      <SelectItem value="HALF_YEARLY">Half Yearly</SelectItem>
                      <SelectItem value="QUARTERLY">Quarterly</SelectItem>
                      <SelectItem value="MONTHLY">Monthly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Parent */}
                <div className="space-y-2">
                  <Label>Parent Period</Label>
                  <Select
                    value={formData.parent ?? "__none__"}
                    onValueChange={(value) =>
                      updateField("parent", value === "__none__" ? null : value)
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">None</SelectItem>
                      {parentPeriods
                        .filter((period) => period.id !== id)
                        .map((period) => (
                          <SelectItem key={period.id} value={period.id}>
                            {period.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Status */}
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(value) =>
                      updateField(
                        "status",
                        value as ReportingPeriodFormData["status"]
                      )
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="OPEN">Open</SelectItem>
                      <SelectItem value="LOCKED">Locked</SelectItem>
                      <SelectItem value="CLOSED">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Start */}
                <div className="space-y-2">
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => updateField("start_date", e.target.value)}
                  />
                </div>

                {/* End */}
                <div className="space-y-2">
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => updateField("end_date", e.target.value)}
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* ---------------- Options ---------------- */}
            <div className="space-y-5">
              <h3 className="text-sm font-semibold text-[#111827]">Options</h3>

              <div className="space-y-3">
                <label
                  htmlFor="is_baseline_year"
                  className="flex cursor-pointer items-start gap-3 rounded-lg border border-[#E5E7EB] p-4 hover:bg-[#FAFBFD]"
                >
                  <Checkbox
                    id="is_baseline_year"
                    checked={formData.is_baseline_year}
                    onCheckedChange={(checked) =>
                      updateField("is_baseline_year", checked === true)
                    }
                    className="mt-0.5"
                  />
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium text-[#111827]">
                      Baseline Year
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Mark this reporting period as the baseline year.
                    </p>
                  </div>
                </label>

                <label
                  htmlFor="is_active"
                  className="flex cursor-pointer items-start gap-3 rounded-lg border border-[#E5E7EB] p-4 hover:bg-[#FAFBFD]"
                >
                  <Checkbox
                    id="is_active"
                    checked={formData.is_active}
                    onCheckedChange={(checked) =>
                      updateField("is_active", checked === true)
                    }
                    className="mt-0.5"
                  />
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium text-[#111827]">Active</p>
                    <p className="text-sm text-muted-foreground">
                      Enable this reporting period.
                    </p>
                  </div>
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ======================================================
            ACTIONS
        ====================================================== */}

        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            className="w-full sm:w-auto"
            onClick={() => navigate("/periods")}
          >
            Cancel
          </Button>

          <Button
            type="submit"
            disabled={saving || loading}
            className="w-full sm:w-auto"
          >
            {saving
              ? "Saving..."
              : isEdit
              ? "Update Reporting Period"
              : "Create Reporting Period"}
          </Button>
        </div>
      </form>
    </AppShell>
  );
}