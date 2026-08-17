import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";
import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import AssessmentCreateDialog from "./AssessmentCreateDialog";

import {
  MoreHorizontal,
} from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type {
  MaterialityAssessment,
  AssessmentStatus,
  AssessmentMode,
} from "@/types/materiality/assessment";

import { Badge } from "@/components/ui/badge";
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
   STATUS LABELS
========================================================== */

const STATUS_LABELS: Record<AssessmentStatus, string> = {
  DRAFT: "Draft",
  IN_PROGRESS: "In Progress",
  COMPLETED: "Completed",
  APPROVED: "Approved",
};

/* ==========================================================
   MODE LABELS
========================================================== */

const MODE_LABELS: Record<AssessmentMode, string> = {
  SINGLE:"Single Materiality",
  DOUBLE: "Double Materiality",
};

/* ==========================================================
   STATUS BADGE
========================================================== */

const getStatusBadge = (status: AssessmentStatus) => {
  switch (status) {
    case "DRAFT":
      return (
        <Badge className="border border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-100">
          Draft
        </Badge>
      );

    case "IN_PROGRESS":
      return (
        <Badge className="border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-50">
          In Progress
        </Badge>
      );

    case "COMPLETED":
      return (
        <Badge className="border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-50">
          Completed
        </Badge>
      );

    case "APPROVED":
      return (
        <Badge className="border border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-50">
          Approved
        </Badge>
      );

    default:
      return <Badge variant="outline">{STATUS_LABELS[status]}</Badge>;
  }
};



/* ==========================================================
   TABLE COLUMNS
========================================================== */

const getAssessmentColumns = ({
  onView,
  onDelete,
  onAddStakeholderGroup,
  onManageSurvey,
  onManageSurveyDistribution,
  onScoring,
  onMatrix
  
}: {
  onView: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (assessment: MaterialityAssessment) => void;
  onAddStakeholderGroup: (id: string) => void;
  onManageSurvey: (id: string) => void;
  onManageSurveyDistribution: (id: string) => void;
  onScoring: (id: string) => void;
  onMatrix: (id: string) => void;
}): ColumnDef<MaterialityAssessment>[] => [
  /* ASSESSMENT NAME */
  {
    accessorKey: "name",
    header: "Assessment",
    cell: ({ row }) => {
      const assessment = row.original;
      return (
        <button
          type="button"
          onClick={() => onView(assessment.id)}
          className="text-left font-medium text-[#22243A] hover:text-[#4A3FD6] hover:underline"
        >
          {assessment.name}
        </button>
      );
    },
  },

  /* REPORTING PERIOD */
/* REPORTING PERIOD */
{
  id: "reporting_period",
  header: "Reporting Period",
  cell: ({ row }) => {
    const period = row.original.reporting_period_details;

    return (
      <span className="text-sm text-[#22243A]">
        {period?.name || "—"}
      </span>
    );
  },
},
  /* MODE */
  {
    accessorKey: "mode",
    header: "Mode",
    cell: ({ row }) => (
      <span className="text-sm text-[#4B5563]">{MODE_LABELS[row.original.mode]}</span>
    ),
  },

  /* STATUS */
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => getStatusBadge(row.original.status),
  },

  /* ACTIONS */
 {
  id: "actions",
  header: "Actions",
  cell: ({ row }) => {
    const assessment = row.original;

    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="
              h-8
              gap-2
              px-3
              text-xs
              font-medium
            "
          >
            Actions
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent
          align="end"
          className="w-56"
        >
          {/* MANAGE TOPICS */}
          <DropdownMenuItem
            onClick={() =>
              onView(assessment.id)
            }
          >
            Manage Topics
          </DropdownMenuItem>

          {/* STAKEHOLDER GROUPS */}
          <DropdownMenuItem
            onClick={() =>
              onAddStakeholderGroup(
                assessment.id
              )
            }
          >
            Manage Stakeholder Groups
          </DropdownMenuItem>

          {/* SURVEY */}
          <DropdownMenuItem
            onClick={() =>
              onManageSurvey(
                assessment.id
              )
            }
          >
            Manage Survey
          </DropdownMenuItem>

          {/* SURVEY DISTRIBUTION */}
          <DropdownMenuItem
            onClick={() =>
              onManageSurveyDistribution(
                assessment.id
              )
            }
          >
            Survey Distribution
          </DropdownMenuItem>

          {/* SCORING */}
          <DropdownMenuItem
            onClick={() =>
              onScoring(
                assessment.id
              )
            }
          >
            Materiality Scoring
          </DropdownMenuItem>

            {/* MATERIALITY MATRIX */}
          <DropdownMenuItem
            onClick={() =>
              onMatrix(assessment.id)
            }
          >
            Materiality Matrix
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          {/* DELETE */}
          <DropdownMenuItem
            className="
              text-red-600
              focus:bg-red-50
              focus:text-red-700
            "
            onClick={() =>
              onDelete(assessment)
            }
          >
            Delete Assessment
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    );
  },
},
];
/* ==========================================================
   COMPONENT
========================================================== */

export default function AssessmentList() {
  const navigate = useNavigate();

  /* --------------------------- navigation --------------------------- */

  const handleAssessmentClick = useCallback(
    (id: string) => {
      navigate(`/materiality/assessments/${id}/select-topics/`);
    },
    [navigate]
  );

  const handleEdit = useCallback(
    (id: string) => {
      navigate(`/materiality/assessments/${id}/edit`);
    },
    [navigate]
  );

  /* --------------------------- states --------------------------- */

  const [assessments, setAssessments] = useState<MaterialityAssessment[]>([]);
  const [loading, setLoading] = useState(false);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [modeFilter, setModeFilter] = useState("All");

  const [selectedAssessment, setSelectedAssessment] =
    useState<MaterialityAssessment | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  /* --------------------------- load assessments --------------------------- */

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
    loadAssessments();
  }, [loadAssessments]);

 
  /* --------------------------- filter assessments --------------------------- */

  const filteredAssessments = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    return assessments.filter((assessment) => {
      const matchesSearch =
        !keyword ||
        assessment.name.toLowerCase().includes(keyword) ||
        assessment.financial_year.toLowerCase().includes(keyword);

      const matchesStatus = statusFilter === "All" || assessment.status === statusFilter;
      const matchesMode = modeFilter === "All" || assessment.mode === modeFilter;

      return matchesSearch && matchesStatus && matchesMode;
    });
  }, [assessments, search, statusFilter, modeFilter]);

  /* --------------------------- delete --------------------------- */

  const handleDelete = useCallback((assessment: MaterialityAssessment) => {
    setSelectedAssessment(assessment);
  }, []);

  const handleAddStakeholderGroup = useCallback(
    (id: string) => {
      navigate(`/materiality/assessments/${id}/stakeholders/`);
    },
    [navigate]
  );

  const handleManageSurvey = useCallback(
  (id: string) => {
    navigate(
      `/materiality/assessments/${id}/survey`
    );
  },
  [navigate]
);

const handleScoring = useCallback(
  (assessmentId: string) => {
    navigate(
      `/materiality/assessments/${assessmentId}/scoring`
    );
  },
  [navigate]
);

const handleMatrix = useCallback(
  (assessmentId: string) => {
    navigate(
      `/materiality/assessments/${assessmentId}/matrix`
    );
  },
  [navigate]
);



 const handleManageSurveyDistribution =
  useCallback(
    (id: string) => {
      navigate(
        `/materiality/assessments/${id}/survey/distribution`
      );
    },
    [navigate]
  );


  const confirmDelete = async () => {
    if (!selectedAssessment) return;

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


  /* --------------------------- table columns --------------------------- */

  const columns = useMemo(
    () =>
      getAssessmentColumns({
        onView: handleAssessmentClick,
        onEdit: handleEdit,
        onDelete: handleDelete,
        onAddStakeholderGroup: handleAddStakeholderGroup,
        onManageSurvey:handleManageSurvey,
        onManageSurveyDistribution:handleManageSurveyDistribution,
        onScoring:handleScoring,
        onMatrix: handleMatrix,
      }),
    [handleAssessmentClick, handleEdit, handleDelete, handleAddStakeholderGroup,handleManageSurvey,handleManageSurveyDistribution,handleScoring,handleMatrix]
  );

  /* --------------------------- export csv --------------------------- */

  const exportAssessments = useCallback(() => {
    const header = [
      "Assessment",
      "Financial Year",
      "Period Start",
      "Period End",
      "Mode",
      "Status",
      "Locked",
    ];

    const rows = filteredAssessments.map((assessment) => [
      assessment.name,
      assessment.financial_year,
      assessment.period_start,
      assessment.period_end,
      MODE_LABELS[assessment.mode],
      STATUS_LABELS[assessment.status],
      assessment.is_locked ? "Yes" : "No",
    ]);

    const csv = [header, ...rows]
      .map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "materiality-assessments.csv";
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);

    URL.revokeObjectURL(url);
  }, [filteredAssessments]);

  /* --------------------------- return --------------------------- */

  return (
    <AppShell
      title="Materiality Assessments"
      description="Create and manage materiality assessments for your organization."
    >
      <div className="space-y-6">
        {/* DATA TABLE */}
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
              {/* MODE FILTER */}
              <Select value={modeFilter} onValueChange={setModeFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Assessment Mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All Modes</SelectItem>
                  <SelectItem value="FINANCIAL">Single Materiality</SelectItem>
                  <SelectItem value="DOUBLE">Double Materiality</SelectItem>
                </SelectContent>
              </Select>

              {/* STATUS FILTER */}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All Status</SelectItem>
                  <SelectItem value="DRAFT">Draft</SelectItem>
                  <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                  <SelectItem value="COMPLETED">Completed</SelectItem>
                  <SelectItem value="APPROVED">Approved</SelectItem>
                </SelectContent>
              </Select>
            </DataTableToolbar>
          }
        />

        {/* CREATE ASSESSMENT DIALOG */}
        <AssessmentCreateDialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
          onSaved={loadAssessments}
        />

        {/* DELETE CONFIRMATION */}
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