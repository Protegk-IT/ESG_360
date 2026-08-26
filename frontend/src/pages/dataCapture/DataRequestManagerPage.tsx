import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { toast } from "sonner";

import type { ColumnDef } from "@tanstack/react-table";

import AppShell from "@/components/layout/AppShell";
import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";

import { AlertCircle, CheckCircle2, Clock3, Eye, FileCheck2, FileText, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

import DataCaptureApi from "@/api/dataCapture/DataCaptureApi";

import { getApiErrorMessage } from "@/services/errors";

import type {
  DataRequestListItem,
  SubmissionStatus,
} from "@/types/dataCapture";

/* ============================================================
   STATUS BADGE
============================================================ */

type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "info"
  | "warning";

function submissionStatusBadge(status: SubmissionStatus | null): {
  label: string;
  variant: BadgeVariant;
} {
  switch (status) {
    case "DRAFT":
      return {
        label: "Draft",
        variant: "warning",
      };

    case "SUBMITTED":
      return {
        label: "Submitted",
        variant: "info",
      };

    case "APPROVED":
      return {
        label: "Approved",
        variant: "success",
      };

    case "REJECTED":
      return {
        label: "Rejected",
        variant: "destructive",
      };

    default:
      return {
        label: "Not Started",
        variant: "outline",
      };
  }
}

/* ============================================================
   COLUMNS
============================================================ */

function getRequestColumns({
  onView,
}: {
  onView: (request: DataRequestListItem) => void;
}): ColumnDef<DataRequestListItem>[] {
  return [
    {
      accessorKey: "datapoint_label",
      header: "Datapoint",
      cell: ({ row }) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-[#22243A]">
            {row.original.datapoint_label}
          </p>

          <p className="truncate font-mono text-xs text-muted-foreground">
            {row.original.datapoint_code}
          </p>
        </div>
      ),
    },

    {
      accessorKey: "org_node_name",
      header: "Organization / Site",
    },

    {
      accessorKey: "reporting_period_name",
      header: "Reporting Period",
    },

    {
      accessorKey: "assignee_username",
      header: "Assignee",
    },

    {
      accessorKey: "due_date",
      header: "Due Date",
      cell: ({ row }) =>
        row.original.due_date ? (
          formatDate(row.original.due_date)
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },

    {
      accessorKey: "submission_status",
      header: "Status",
      cell: ({ row }) => {
        const { label, variant } = submissionStatusBadge(
          row.original.submission_status,
        );

        return <Badge variant={variant}>{label}</Badge>;
      },
    },

    {
      id: "actions",
      header: () => <div className="text-right">Actions</div>,

      cell: ({ row }) => (
        <div className="flex justify-end">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onView(row.original)}
            aria-label="Manage request"
            title="Manage request"
          >
            <Eye className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];
}

/* ============================================================
   DATE FORMATTER
============================================================ */

function formatDate(value: string) {
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);

  const date = dateOnlyMatch
    ? new Date(
        Number(dateOnlyMatch[1]),
        Number(dateOnlyMatch[2]) - 1,
        Number(dateOnlyMatch[3]),
      )
    : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

/* ============================================================
   COMPONENT
   ------------------------------------------------------------
   Route: /data-capture/manage
============================================================ */

export default function DataRequestManagerPage() {
  const navigate = useNavigate();

  const [requests, setRequests] = useState<DataRequestListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  /* ==========================================================
     LOAD REQUESTS
  ========================================================== */

  const loadRequests = async () => {
    try {
      setLoading(true);

      const response = await DataCaptureApi.getAll({
        page_size: 100,
      });

      setRequests(response.data.data?.results ?? []);
    } catch (error) {
      console.error("Failed to load data requests:", error);

      toast.error(
        getApiErrorMessage(
          error,
          "Failed to load data requests. Please try again.",
        ),
      );

      setRequests([]);
    } finally {
      setLoading(false);
    }
  };

  /* ==========================================================
     INITIAL LOAD
  ========================================================== */

  useEffect(() => {
    let ignore = false;

    queueMicrotask(() => {
      if (!ignore) {
        void loadRequests();
      }
    });

    return () => {
      ignore = true;
    };
  }, []);

  /* ==========================================================
     KPI COUNTS
  ========================================================== */

  const kpis = useMemo(() => {
    const draft = requests.filter(
      (request) => request.submission_status === "DRAFT",
    ).length;

    const submitted = requests.filter(
      (request) => request.submission_status === "SUBMITTED",
    ).length;

    const approved = requests.filter(
      (request) => request.submission_status === "APPROVED",
    ).length;

    const attention = requests.filter((request) => {
      if (!request.due_date) {
        return false;
      }

      if (request.status !== "OPEN") {
        return false;
      }

      if (request.submission_status === "APPROVED") {
        return false;
      }

      const today = new Date();
      const dueDate = new Date(request.due_date);

      today.setHours(0, 0, 0, 0);
      dueDate.setHours(0, 0, 0, 0);

      const daysRemaining =
        (dueDate.getTime() - today.getTime()) /
        (1000 * 60 * 60 * 24);

      return daysRemaining <= 3;
    }).length;

    return {
      total: requests.length,
      draft,
      submitted,
      approved,
      attention,
    };
  }, [requests]);

  /* ==========================================================
     ALERT COUNTS
  ========================================================== */

  const alerts = useMemo(() => {
    const overdue = requests.filter((request) => {
      if (!request.due_date) {
        return false;
      }

      if (request.status !== "OPEN") {
        return false;
      }

      if (request.submission_status === "APPROVED") {
        return false;
      }

      const today = new Date();
      const dueDate = new Date(request.due_date);

      today.setHours(0, 0, 0, 0);
      dueDate.setHours(0, 0, 0, 0);

      return dueDate.getTime() < today.getTime();
    }).length;

    const dueSoon = requests.filter((request) => {
      if (!request.due_date) {
        return false;
      }

      if (request.status !== "OPEN") {
        return false;
      }

      if (request.submission_status === "APPROVED") {
        return false;
      }

      const today = new Date();
      const dueDate = new Date(request.due_date);

      today.setHours(0, 0, 0, 0);
      dueDate.setHours(0, 0, 0, 0);

      const daysRemaining =
        (dueDate.getTime() - today.getTime()) /
        (1000 * 60 * 60 * 24);

      return daysRemaining >= 0 && daysRemaining <= 3;
    }).length;

    return {
      overdue,
      dueSoon,
    };
  }, [requests]);

  /* ==========================================================
     FILTERED REQUESTS
  ========================================================== */

  const filteredRequests = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (keyword === "") {
      return requests;
    }

    return requests.filter(
      (request) =>
        request.datapoint_label.toLowerCase().includes(keyword) ||
        request.datapoint_code.toLowerCase().includes(keyword) ||
        request.org_node_name.toLowerCase().includes(keyword) ||
        request.assignee_username.toLowerCase().includes(keyword),
    );
  }, [requests, search]);

  /* ==========================================================
     TABLE COLUMNS
  ========================================================== */

  const columns = useMemo(
    () =>
      getRequestColumns({
        onView: (request) =>
          navigate(`/data-capture/manage/${request.id}`),
      }),
    [navigate],
  );

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      title="Manage Data Requests"
      description="Create and oversee M5 data collection requests."
    >
      <div className="mt-6 space-y-6">
        {/* ==================================================
            HEADER
        ================================================== */}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[#22243A]">
              Data Requests
            </h2>

            <p className="text-sm text-muted-foreground">
              Create and oversee M5 data collection requests.
            </p>
          </div>

          <Button
            type="button"
            onClick={() =>
              navigate("/data-capture/requests/create")
            }
          >
            Create Request
          </Button>
        </div>

        {/* ==================================================
            KPI CARDS
        ================================================== */}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <KpiCard
            title="Total"
            value={kpis.total}
            description="Total data requests"
            icon={FileText}
            className="border-blue-200 bg-blue-50/60"
            iconClassName="bg-blue-100 text-blue-600"
          />

          <KpiCard
            title="Draft"
            value={kpis.draft}
            description="Work saved as draft"
            icon={Clock3}
            className="border-amber-200 bg-amber-50/60"
            iconClassName="bg-amber-100 text-amber-600"
          />

          <KpiCard
            title="Submitted"
            value={kpis.submitted}
            description="Waiting for review"
            icon={FileCheck2}
            className="border-violet-200 bg-violet-50/60"
            iconClassName="bg-violet-100 text-violet-600"
          />

          <KpiCard
            title="Approved"
            value={kpis.approved}
            description="Successfully approved"
            icon={CheckCircle2}
            className="border-emerald-200 bg-emerald-50/60"
            iconClassName="bg-emerald-100 text-emerald-600"
          />

          <KpiCard
            title="Attention"
            value={kpis.attention}
            description="Due within 3 days"
            icon={AlertCircle}
            className="border-rose-200 bg-rose-50/60"
            iconClassName="bg-rose-100 text-rose-600"
          />
        </div>

        {/* ==================================================
            ALERTS
        ================================================== */}

        {(alerts.overdue > 0 || alerts.dueSoon > 0) && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-[#22243A]" />

              <div>
                <h2 className="text-base font-semibold text-[#22243A]">
                  Attention Required
                </h2>

                <p className="text-sm text-[#6B7280]">
                  Keep your data collection requests on schedule.
                </p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {/* OVERDUE */}

              {alerts.overdue > 0 && (
                <Card className="border-red-200 bg-gradient-to-r from-red-50 to-white shadow-sm">
                  <CardContent className="p-5">
                    <div className="flex items-start gap-4">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-100">
                        <AlertCircle className="h-5 w-5 text-red-600" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-red-900">
                            Overdue data requests
                          </h3>

                          <Badge variant="destructive">
                            {alerts.overdue}
                          </Badge>
                        </div>

                        <p className="mt-1.5 text-sm leading-6 text-red-700">
                          {alerts.overdue === 1
                            ? "One data request has passed its due date."
                            : `${alerts.overdue} data requests have passed their due dates.`}
                        </p>

                        <p className="mt-2 text-xs font-medium text-red-600">
                          Please review these requests as soon as possible.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* DUE SOON */}

              {alerts.dueSoon > 0 && (
                <Card className="border-amber-200 bg-gradient-to-r from-amber-50 to-white shadow-sm">
                  <CardContent className="p-5">
                    <div className="flex items-start gap-4">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-100">
                        <Clock3 className="h-5 w-5 text-amber-600" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-amber-900">
                            Due soon
                          </h3>

                          <Badge variant="warning">
                            {alerts.dueSoon}
                          </Badge>
                        </div>

                        <p className="mt-1.5 text-sm leading-6 text-amber-700">
                          {alerts.dueSoon === 1
                            ? "One data request is due within the next 3 days."
                            : `${alerts.dueSoon} data requests are due within the next 3 days.`}
                        </p>

                        <p className="mt-2 text-xs font-medium text-amber-600">
                          Review the requests below to track progress.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* ==================================================
            REQUEST TABLE
        ================================================== */}

        <DataTable
          columns={columns}
          data={filteredRequests}
          loading={loading}
          emptyMessage={
            search
              ? "No requests match your search."
              : "No data requests yet. Create the first one to get started."
          }
          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}
            >
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  void loadRequests();
                }}
                disabled={loading}
                className="h-9 shrink-0"
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${
                    loading ? "animate-spin" : ""
                  }`}
                />

                Refresh
              </Button>
            </DataTableToolbar>
          }
        />
      </div>
    </AppShell>
  );
}

/* ==========================================================
   KPI CARD
========================================================== */

interface KpiCardProps {
  title: string;
  value: number;
  description: string;
  icon: React.ComponentType<{
    className?: string;
  }>;
  className?: string;
  iconClassName?: string;
}

function KpiCard({
  title,
  value,
  description,
  icon: Icon,
  className,
  iconClassName,
}: KpiCardProps) {
  return (
    <Card
      className={`overflow-hidden transition-shadow hover:shadow-md ${
        className ?? ""
      }`}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-[#6B7280]">
              {title}
            </p>

            <p className="mt-2 text-3xl font-bold tracking-tight text-[#22243A]">
              {value}
            </p>

            <p className="mt-1 text-xs leading-5 text-[#6B7280]">
              {description}
            </p>
          </div>

          <div
            className={`shrink-0 rounded-xl p-2.5 ${
              iconClassName ?? ""
            }`}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}