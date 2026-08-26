import { useCallback, useEffect, useMemo, useState } from "react";

import { useNavigate } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import AssessmentCreateDialog from "./AssessmentCreateDialog";

import { Check, Circle, Trash2 } from "lucide-react";

import type {
  MaterialityAssessment,
  AssessmentStatus,
  AssessmentMode,
} from "@/types/materiality/assessment";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { type ColumnDef } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";

/* ==========================================================
   TYPES
========================================================== */

/*
 * Your existing MaterialityAssessment type can continue
 * to be used.

 * These fields are optional so this UI works even before
 * the backend serializer is updated.
 *
 * Recommended backend response:
 *
 * {
 *   "progress_percentage": 57,
 *   "current_step": "Manage Survey"
 * }
 */

type AssessmentWithProgress = MaterialityAssessment & {
  progress_percentage?: number | null;
  progress?: number | null;
  current_step?: string | null;
  current_step_url?: string | null;
  completed_steps?: number | null;
  total_steps?: number | null;
};

/* ==========================================================
   STATUS LABELS
========================================================== */

const STATUS_LABELS: Record<AssessmentStatus, string> = {
  DRAFT: "Draft",
  IN_PROGRESS: "In Progress",
  SCORED: "Scored",
  COMPLETED: "Completed",
  APPROVED: "Approved",
};

/* ==========================================================
   MODE LABELS
========================================================== */

const MODE_LABELS: Record<AssessmentMode, string> = {
  SINGLE: "Single Materiality",
  DOUBLE: "Double Materiality",
};

/* ==========================================================
   ASSESSMENT WORKFLOW
========================================================== */

const ASSESSMENT_STEPS = [
  "Assessment Overview",
  "Manage Topics",
  "Manage Stakeholder Groups",
  "Manage Survey",
  "Survey Distribution",
  "Materiality Scoring",
  "Materiality Matrix",
];

/* ==========================================================
   PROGRESS HELPER
========================================================== */

const clampProgress = (value: number) => {
  return Math.min(100, Math.max(0, Math.round(value)));
};

/* ==========================================================
   GET PROGRESS
========================================================== */

const getAssessmentProgress = (assessment: AssessmentWithProgress): number => {
  /*
   * COMPLETED / APPROVED
   *
   * These are always 100%.
   */

  if (
    assessment.status === "SCORED" ||
    assessment.status === "COMPLETED" ||
    assessment.status === "APPROVED"
  ) {
    return 100;
  }

  /*
   * PRIMARY BACKEND VALUE
   *
   * Recommended field:
   *
   * progress_percentage
   */

  if (typeof assessment.progress_percentage === "number") {
    return clampProgress(assessment.progress_percentage);
  }

  /*
   * SECONDARY BACKEND VALUE
   */

  if (typeof assessment.progress === "number") {
    return clampProgress(assessment.progress);
  }

  /*
   * COMPLETED STEPS
   *
   * Example:
   *
   * completed_steps = 4
   * total_steps = 7
   *
   * => 57%
   */

  if (
    typeof assessment.completed_steps === "number" &&
    typeof assessment.total_steps === "number" &&
    assessment.total_steps > 0
  ) {
    return clampProgress(
      (assessment.completed_steps / assessment.total_steps) * 100,
    );
  }

  /*
   * CURRENT STEP
   *
   * If backend returns:
   *
   * current_step: "Manage Survey"
   *
   * calculate progress from workflow.
   */

  if (assessment.current_step) {
    const currentIndex = ASSESSMENT_STEPS.indexOf(assessment.current_step);

    if (currentIndex >= 0) {
      return clampProgress((currentIndex / ASSESSMENT_STEPS.length) * 100);
    }
  }

  /*
   * SAFE FALLBACK
   *
   * We don't invent a fake percentage.
   *
   * DRAFT = 0
   * IN_PROGRESS = 0 until backend progress exists
   */

  if (assessment.status === "DRAFT") {
    return 0;
  }

  return 0;
};

/* ==========================================================
   CURRENT STEP LABEL
========================================================== */

const getCurrentStepLabel = (
  assessment: AssessmentWithProgress,
  progress: number,
) => {
  /*
   * Completed
   */

  if (
    assessment.status === "SCORED" ||
    assessment.status === "COMPLETED" ||
    assessment.status === "APPROVED" ||
    progress >= 100
  ) {
    return "Completed";
  }

  /*
   * Backend current step
   */

  if (assessment.current_step) {
    return assessment.current_step;
  }

  /*
   * No progress information yet
   */

  if (progress === 0) {
    return "Assessment started";
  }

  /*
   * Calculate approximate step
   */

  const stepIndex = Math.min(
    ASSESSMENT_STEPS.length - 1,
    Math.floor((progress / 100) * ASSESSMENT_STEPS.length),
  );

  return ASSESSMENT_STEPS[stepIndex];
};

/* ==========================================================
   PROGRESS COMPONENT
========================================================== */

function AssessmentProgress({
  assessment,
}: {
  assessment: AssessmentWithProgress;
}) {
  const progress = getAssessmentProgress(assessment);

  const completed =
    progress >= 100 ||
    assessment.status === "SCORED" ||
    assessment.status === "COMPLETED" ||
    assessment.status === "APPROVED";

  const currentStep = getCurrentStepLabel(assessment, progress);

  return (
    <div className="min-w-[190px] max-w-[250px]">
      {/* Percentage + Step */}

      <div className="mb-1.5 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          {completed ? (
            <div
              className="
                flex
                h-5
                w-5
                shrink-0
                items-center
                justify-center
                rounded-full
                bg-emerald-100
                text-emerald-600
              "
            >
              <Check className="h-3 w-3" />
            </div>
          ) : (
            <Circle
              className="
                h-4
                w-4
                shrink-0
                text-[#4A3FD6]
              "
            />
          )}

          <span
            className="
              text-sm
              font-semibold
              text-[#22243A]
            "
          >
            {progress}%
          </span>
        </div>

        <span
          className="
            truncate
            text-[11px]
            font-medium
            text-slate-500
          "
          title={currentStep}
        >
          {currentStep}
        </span>
      </div>

      {/* Progress Bar */}

      <div
        className="
          h-2
          w-full
          overflow-hidden
          rounded-full
          bg-slate-100
        "
      >
        <div
          className={`
            h-full
            rounded-full
            transition-all
            duration-500
            ${completed ? "bg-emerald-500" : "bg-[#4A3FD6]"}
          `}
          style={{
            width: `${progress}%`,
          }}
        />
      </div>

      {/* Completed label */}

      {completed && (
        <div
          className="
            mt-1.5
            flex
            items-center
            gap-1
            text-[11px]
            font-medium
            text-emerald-600
          "
        >
          <Check className="h-3 w-3" />
          Assessment completed
        </div>
      )}
    </div>
  );
}

/* ==========================================================
   TABLE COLUMNS
========================================================== */

const getAssessmentColumns = ({
  onContinue,
  onDelete,
}: {
  onContinue: (id: string) => void;

  onDelete: (assessment: MaterialityAssessment) => void;
}): ColumnDef<MaterialityAssessment>[] => [
  /* ========================================================
     ASSESSMENT
  ======================================================== */

  {
    accessorKey: "name",

    header: "Assessment",

    cell: ({ row }) => {
      const assessment = row.original;

      return (
        <div className="min-w-[220px]">
          <button
            type="button"
            onClick={() => onContinue(assessment.id)}
            className="
              text-left
              font-semibold
              text-[#22243A]
              transition-colors
              hover:text-[#4A3FD6]
            "
          >
            {assessment.name}
          </button>

          <p
            className="
              mt-1
              text-xs
              text-slate-500
            "
          >
            {MODE_LABELS[assessment.mode]}
          </p>
        </div>
      );
    },
  },

  /* ========================================================
     REPORTING PERIOD
  ======================================================== */

  {
    id: "reporting_period",

    header: "Reporting Period",

    cell: ({ row }) => {
      const period = row.original.reporting_period_details;

      return (
        <span
          className="
            text-sm
            text-[#22243A]
          "
        >
          {period?.name || "—"}
        </span>
      );
    },
  },

  /* ========================================================
     PROGRESS
  ======================================================== */

  {
    id: "progress",

    header: "Progress",

    cell: ({ row }) => {
      const assessment = row.original as AssessmentWithProgress;

      return <AssessmentProgress assessment={assessment} />;
    },
  },

  /* ========================================================
     ACTION
  ======================================================== */

  {
    id: "action",

    header: "Action",

    cell: ({ row }) => {
      const assessment = row.original as AssessmentWithProgress;

      const progress = getAssessmentProgress(assessment);

      const completed =
        progress >= 100 ||
        assessment.status === "SCORED" ||
        assessment.status === "COMPLETED" ||
        assessment.status === "APPROVED";

      return (
        <div className="flex items-center gap-2">
          {/* CONTINUE / COMPLETED */}

          {completed ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => onContinue(assessment.id)}
              className="h-9 rounded-lg border-emerald-200 bg-emerald-50 px-3 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
            >
              <Check className="mr-1.5 h-3.5 w-3.5" />
              View
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={() => onContinue(assessment.id)}
              className="
                h-9
                rounded-lg
                bg-[#4A3FD6]
                px-4
                text-xs
                font-semibold
                text-white
                shadow-sm
                transition-all
                hover:bg-[#3F34C2]
                hover:shadow
              "
            >
              Continue
            </Button>
          )}

          {/* DELETE */}

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => onDelete(assessment)}
            className="
              h-9
              w-9
              rounded-lg
              text-slate-400
              transition-colors
              hover:bg-red-50
              hover:text-red-600
            "
            aria-label={`Delete ${assessment.name}`}
          >
            <Trash2
              className="
                h-4
                w-4
              "
            />
          </Button>
        </div>
      );
    },
  },
];

/* ==========================================================
   COMPONENT
========================================================== */

export default function AssessmentList() {
  const navigate = useNavigate();

  /* ========================================================
     STATES
  ======================================================== */

  const [assessments, setAssessments] = useState<MaterialityAssessment[]>([]);

  const [loading, setLoading] = useState(false);

  const [search, setSearch] = useState("");

  const [modeFilter, setModeFilter] = useState("All");

  const [selectedAssessment, setSelectedAssessment] =
    useState<MaterialityAssessment | null>(null);

  const [deleting, setDeleting] = useState(false);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  /* ========================================================
     LOAD ASSESSMENTS
  ======================================================== */

  const loadAssessments = useCallback(async () => {
    try {
      setLoading(true);

      const response = await AssessmentApi.getAll();

      setAssessments(response.data);
    } catch (error) {
      console.error("Failed to load materiality assessments:", error);
    } finally {
      setLoading(false);
    }
  }, []);

useEffect(() => {
  const load = async () => {
    await loadAssessments();
  };

  void load();
}, [loadAssessments]);

  /* ========================================================
     CONTINUE ASSESSMENT
  ======================================================== */

  const handleContinue = useCallback(
    (id: string) => {
      navigate(`/materiality/assessments/${id}`);
    },
    [navigate],
  );

  /* ========================================================
     DELETE
  ======================================================== */

  const handleDelete = useCallback((assessment: MaterialityAssessment) => {
    setSelectedAssessment(assessment);
  }, []);

  /* ========================================================
     FILTER
  ======================================================== */

  const filteredAssessments = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    return assessments.filter((assessment) => {
      const matchesSearch =
        !keyword ||
        assessment.name.toLowerCase().includes(keyword) ||
        assessment.financial_year.toLowerCase().includes(keyword);

      const matchesMode =
        modeFilter === "All" || assessment.mode === modeFilter;

      return matchesSearch && matchesMode;
    });
  }, [assessments, search, modeFilter]);

  /* ========================================================
     CONFIRM DELETE
  ======================================================== */

  const confirmDelete = async () => {
    if (!selectedAssessment) {
      return;
    }

    try {
      setDeleting(true);

      await AssessmentApi.delete(selectedAssessment.id);

      await loadAssessments();

      setSelectedAssessment(null);
    } catch (error) {
      console.error("Failed to delete assessment:", error);
    } finally {
      setDeleting(false);
    }
  };

  /* ========================================================
     TABLE COLUMNS
  ======================================================== */

  const columns = useMemo(
    () =>
      getAssessmentColumns({
        onContinue: handleContinue,

        onDelete: handleDelete,
      }),
    [handleContinue, handleDelete],
  );

  /* ========================================================
     EXPORT CSV
  ======================================================== */

  const exportAssessments = useCallback(() => {
    const header = [
      "Assessment",
      "Reporting Period",
      "Mode",
      "Progress",
      "Status",
    ];

    const rows = filteredAssessments.map((assessment) => {
      const assessmentWithProgress = assessment as AssessmentWithProgress;

      const progress = getAssessmentProgress(assessmentWithProgress);

      return [
        assessment.name,
        assessment.reporting_period_details?.name ?? "",
        MODE_LABELS[assessment.mode],
        `${progress}%`,
        STATUS_LABELS[assessment.status],
      ];
    });

    const csv = [header, ...rows]
      .map((row) =>
        row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","),
      )
      .join("\n");

    const blob = new Blob([csv], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);

    const anchor = document.createElement("a");

    anchor.href = url;

    anchor.download = "materiality-assessments.csv";

    document.body.appendChild(anchor);

    anchor.click();

    document.body.removeChild(anchor);

    URL.revokeObjectURL(url);
  }, [filteredAssessments]);

  /* ========================================================
     RETURN
  ======================================================== */

  return (
    <AppShell
      title="Materiality Assessments"
      description="Create and manage materiality assessments for your organization."
    >
      <div className="space-y-6">
        {/* ==================================================
            TABLE
        ================================================== */}

        <DataTable
          columns={columns}
          data={filteredAssessments}
          loading={loading}
          emptyMessage="No materiality assessments found."

          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}

              addLabel="Create Assessment"

              onAdd={() => setCreateDialogOpen(true)}

              onExport={exportAssessments}
            >
              {/* ==========================================
                  MODE FILTER
              ========================================== */}

              <Select value={modeFilter} onValueChange={setModeFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Assessment Mode" />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="All">All Modes</SelectItem>

                  <SelectItem value="SINGLE">Single Materiality</SelectItem>

                  <SelectItem value="DOUBLE">Double Materiality</SelectItem>
                </SelectContent>
              </Select>
            </DataTableToolbar>
          }
        />

        {/* ==================================================
            CREATE ASSESSMENT
        ================================================== */}

        <AssessmentCreateDialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
          onSaved={loadAssessments}
        />

        {/* ==================================================
            DELETE CONFIRMATION
        ================================================== */}

        <ConfirmDialog
          open={selectedAssessment !== null}

          title="Delete Assessment"

          description={
            selectedAssessment
              ? `Are you sure you want to delete "${selectedAssessment.name}"? This action cannot be undone.`
              : ""
          }

          confirmText="Delete Assessment"

          loading={deleting}

          onConfirm={confirmDelete}

          onCancel={() => setSelectedAssessment(null)}
        />
      </div>
    </AppShell>
  );
}
