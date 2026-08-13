import { useEffect, useMemo, useState } from "react";

import { useNavigate } from "react-router-dom";

import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import ReportingPeriodApi from "@/api/reporting_periods/ReportingPeriodApi";

import type {
  ReportingPeriod,
  GenerateSubPeriodsPayload,
} from "@/types/reporting-period";

import { getReportingPeriodColumns } from "./reporting-period-columns";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

export default function ReportingPeriodList() {
  const navigate = useNavigate();

  /* ==========================================================
      STATE
  ========================================================== */

  const [periods, setPeriods] =
    useState<ReportingPeriod[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("All");

  const [typeFilter, setTypeFilter] =
    useState("All");

  const [selectedPeriod, setSelectedPeriod] =
    useState<ReportingPeriod | null>(null);

  const [deleting, setDeleting] =
    useState(false);

  const [locking, setLocking] =
    useState(false);

  const [unlocking, setUnlocking] =
    useState(false);

  const [generating, setGenerating] =
    useState(false);

  const [generateType, setGenerateType] =
    useState<
      GenerateSubPeriodsPayload["period_type"]
    >("QUARTERLY");

  const [dialogMode, setDialogMode] =
    useState<
      | "delete"
      | "lock"
      | "unlock"
      | "generate"
      | null
    >(null);

  /* ==========================================================
      LOAD PERIODS
  ========================================================== */

  const loadPeriods =
    async () => {
      try {
        setLoading(true);

        const response =
          await ReportingPeriodApi.getAll();

        setPeriods(response.data);
      } catch (error) {
        console.error(error);

        toast.error(
          "Unable to load reporting periods."
        );
      } finally {
        setLoading(false);
      }
    };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadPeriods();
  }, []);

  /* ==========================================================
      FILTERS
  ========================================================== */

  const filteredPeriods =
    useMemo(() => {
      return periods.filter(
        (period) => {
          const keyword =
            search.toLowerCase();

          const matchesSearch =
            period.name
              .toLowerCase()
              .includes(keyword);

          const matchesStatus =
            statusFilter === "All" ||
            period.status ===
              statusFilter;

          const matchesType =
            typeFilter === "All" ||
            period.period_type ===
              typeFilter;

          return (
            matchesSearch &&
            matchesStatus &&
            matchesType
          );
        }
      );
    }, [
      periods,
      search,
      statusFilter,
      typeFilter,
    ]);

  /* ==========================================================
      EXPORT CSV
  ========================================================== */

  const exportPeriods =
    () => {
      const csv = [
        [
          "Name",
          "Type",
          "Start Date",
          "End Date",
          "Status",
          "Baseline",
        ],

        ...filteredPeriods.map(
          (period) => [
            period.name,

            period.period_type,

            period.start_date,

            period.end_date,

            period.status,

            period.is_baseline_year
              ? "Yes"
              : "No",
          ]
        ),
      ]
        .map((row) =>
          row.join(",")
        )
        .join("\n");

      const blob =
        new Blob([csv]);

      const url =
        URL.createObjectURL(
          blob
        );

      const a =
        document.createElement(
          "a"
        );

      a.href = url;

      a.download =
        "reporting-periods.csv";

      a.click();

      URL.revokeObjectURL(url);
    };

  /* ==========================================================
      ACTIONS
  ========================================================== */

  const handleView = (
    id: string
  ) => {
    navigate(
      `/periods/${id}`
    );
  };

  const handleEdit = (
    id: string
  ) => {
    navigate(
      `/periods/${id}/edit`
    );
  };

  const handleDelete = (
    period: ReportingPeriod
  ) => {
    setSelectedPeriod(period);

    setDialogMode(
      "delete"
    );
  };

  const handleLock = (
    period: ReportingPeriod
  ) => {
    setSelectedPeriod(period);

    setDialogMode(
      "lock"
    );
  };

  const handleUnlock = (
    period: ReportingPeriod
  ) => {
    setSelectedPeriod(period);

    setDialogMode(
      "unlock"
    );
  };

  const handleGenerate = (
    period: ReportingPeriod
  ) => {
    setSelectedPeriod(period);

    setGenerateType(
      "QUARTERLY"
    );

    setDialogMode(
      "generate"
    );
  };

    /* ==========================================================
      CONFIRM DELETE
  ========================================================== */

  const confirmDelete = async () => {
    if (!selectedPeriod) return;

    try {
      setDeleting(true);

      await ReportingPeriodApi.delete(
        selectedPeriod.id
      );

      toast.success(
        "Reporting period deleted successfully."
      );

      await loadPeriods();

      setDialogMode(null);

      setSelectedPeriod(null);
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to delete reporting period."
      );
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
      CONFIRM LOCK
  ========================================================== */

  const confirmLock = async () => {
    if (!selectedPeriod) return;

    try {
      setLocking(true);

      await ReportingPeriodApi.lock(
        selectedPeriod.id
      );

      toast.success(
        "Reporting period locked successfully."
      );

      await loadPeriods();

      setDialogMode(null);

      setSelectedPeriod(null);
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to lock reporting period."
      );
    } finally {
      setLocking(false);
    }
  };

  /* ==========================================================
      CONFIRM UNLOCK
  ========================================================== */

  const confirmUnlock = async () => {
    if (!selectedPeriod) return;

    try {
      setUnlocking(true);

      await ReportingPeriodApi.unlock(
        selectedPeriod.id
      );

      toast.success(
        "Reporting period unlocked successfully."
      );

      await loadPeriods();

      setDialogMode(null);

      setSelectedPeriod(null);
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to unlock reporting period."
      );
    } finally {
      setUnlocking(false);
    }
  };

  /* ==========================================================
      GENERATE SUB PERIODS
  ========================================================== */

  const confirmGenerate = async () => {
    if (!selectedPeriod) return;

    try {
      setGenerating(true);

      await ReportingPeriodApi.generateSubPeriods(
        selectedPeriod.id,
        {
          period_type:
            generateType,
        }
      );

      toast.success(
        "Sub-periods generated successfully."
      );

      await loadPeriods();

      setDialogMode(null);

      setSelectedPeriod(null);
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to generate sub-periods."
      );
    } finally {
      setGenerating(false);
    }
  };

  /* ==========================================================
      TABLE COLUMNS
  ========================================================== */

  const columns =
    getReportingPeriodColumns({
      onView:
        handleView,

      onEdit:
        handleEdit,

      onDelete:
        handleDelete,

      onLock:
        handleLock,

      onUnlock:
        handleUnlock,

      onGenerate:
        handleGenerate,
      canGenerate: (period) =>
        period.period_type === "ANNUAL" &&
        period.status === "OPEN" &&
        (period.children_count ?? 0) === 0,
    });
      /* ==========================================================
      UI
  ========================================================== */

  return (
    <AppShell
      title="Reporting Periods"
      description="Manage annual and sub-reporting periods."
    >
      <DataTable
        columns={columns}
        data={filteredPeriods}
        loading={loading}
        emptyMessage="No reporting periods found."
        toolbar={
          <DataTableToolbar
            search={search}
            onSearchChange={setSearch}
            addLabel="Add Reporting Period"
            onAdd={() =>
              navigate("/periods/create")
            }
            onExport={exportPeriods}
          >
            {/* ======================================
                PERIOD TYPE
            ====================================== */}

            <Select
              value={typeFilter}
              onValueChange={setTypeFilter}
            >
              <SelectTrigger className="w-48">

                <SelectValue placeholder="Period Type" />

              </SelectTrigger>

              <SelectContent>

                <SelectItem value="All">

                  All Types

                </SelectItem>

                <SelectItem value="ANNUAL">

                  Annual

                </SelectItem>

                <SelectItem value="HALF_YEARLY">

                  Half Yearly

                </SelectItem>

                <SelectItem value="QUARTERLY">

                  Quarterly

                </SelectItem>

                <SelectItem value="MONTHLY">

                  Monthly

                </SelectItem>

              </SelectContent>

            </Select>

            {/* ======================================
                STATUS
            ====================================== */}

            <Select
              value={statusFilter}
              onValueChange={setStatusFilter}
            >
              <SelectTrigger className="w-40">

                <SelectValue placeholder="Status" />

              </SelectTrigger>

              <SelectContent>

                <SelectItem value="All">

                  All Status

                </SelectItem>

                <SelectItem value="OPEN">

                  Open

                </SelectItem>

                <SelectItem value="LOCKED">

                  Locked

                </SelectItem>

                <SelectItem value="CLOSED">

                  Closed

                </SelectItem>

              </SelectContent>

            </Select>

          </DataTableToolbar>
        }
      />

      {/* ==========================================================
          DELETE
      ========================================================== */}

      <ConfirmDialog
        open={dialogMode === "delete"}
        title="Delete Reporting Period"
        description={`Are you sure you want to delete "${selectedPeriod?.name}"? This action cannot be undone.`}
        confirmText="Delete Reporting Period"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => {
          setDialogMode(null);
          setSelectedPeriod(null);
        }}
      />

      {/* ==========================================================
          LOCK
      ========================================================== */}

      <ConfirmDialog
        open={dialogMode === "lock"}
        title="Lock Reporting Period"
        description={`Lock "${selectedPeriod?.name}"?\n\nAfter locking:\n• ESG data cannot be created.\n• Existing ESG data cannot be edited.\n• Existing ESG data cannot be deleted.\n\nThe reporting period becomes read-only until it is unlocked.`}
        confirmText="Lock Period"
        loading={locking}
        onConfirm={confirmLock}
        onCancel={() => {
          setDialogMode(null);
          setSelectedPeriod(null);
        }}
      />

      {/* ==========================================================
          UNLOCK
      ========================================================== */}

      <ConfirmDialog
        open={dialogMode === "unlock"}
        title="Unlock Reporting Period"
        description={`Unlock "${selectedPeriod?.name}"?\n\nUsers will be able to modify ESG data within this reporting period again.`}
        confirmText="Unlock Period"
        loading={unlocking}
        onConfirm={confirmUnlock}
        onCancel={() => {
          setDialogMode(null);
          setSelectedPeriod(null);
        }}
      />

      {/* ==========================================================
          GENERATE SUB PERIODS
      ========================================================== */}
<Dialog
  open={dialogMode === "generate"}
  onOpenChange={(open) => {
    if (!open) {
      setDialogMode(null);
      setSelectedPeriod(null);
    }
  }}
>
  <DialogContent className="bg-white sm:max-w-md">
    <DialogHeader>
      <DialogTitle>
        Generate Sub Periods
      </DialogTitle>

      <DialogDescription>
        Generate sub-reporting periods for{" "}
        <span className="font-semibold">
          {selectedPeriod?.name}
        </span>
        .
      </DialogDescription>
    </DialogHeader>

    <div className="space-y-4 py-2">

      <div className="space-y-2">
        <Label>Sub Period Type</Label>

        <Select
          value={generateType}
          onValueChange={(value) =>
            setGenerateType(
              value as
                | "HALF_YEARLY"
                | "QUARTERLY"
                | "MONTHLY"
            )
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Select Type" />
          </SelectTrigger>

          <SelectContent>
            <SelectItem value="HALF_YEARLY">
              Half Yearly
            </SelectItem>

            <SelectItem value="QUARTERLY">
              Quarterly
            </SelectItem>

            <SelectItem value="MONTHLY">
              Monthly
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

    </div>

    <DialogFooter>
      <Button
        variant="outline"
        onClick={() => {
          setDialogMode(null);
          setSelectedPeriod(null);
        }}
      >
        Cancel
      </Button>

      <Button
        onClick={confirmGenerate}
        disabled={generating}
      >
        {generating
          ? "Generating..."
          : "Generate"}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
    </AppShell>
  );
}
