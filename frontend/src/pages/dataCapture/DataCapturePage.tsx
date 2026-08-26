import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  FileText,
  RefreshCw,
} from "lucide-react";

import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";
import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import DataCaptureApi from "@/api/dataCapture/DataCaptureApi";

import type {
  DataRequestListItem,
  SubmissionStatus,
} from "@/types/dataCapture";

import type { ColumnDef } from "@tanstack/react-table";

import { getApiErrorMessage } from "@/services/errors";

/* ==========================================================
   DATA CAPTURE PAGE
========================================================== */

export default function DataCapturePage() {
  const navigate = useNavigate();

  /* ========================================================
     STATE
  ======================================================== */

  const [requests, setRequests] = useState<DataRequestListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] =
    useState<"All" | SubmissionStatus>("All");

  /* ========================================================
     LOAD REQUESTS

     Uses the real M5 "My Requests" endpoint.

     The effect uses an internal async function instead of
     directly calling an async state-changing function from
     the effect body.
  ======================================================== */

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);

      const response = await DataCaptureApi.getMine({
        page_size: 100,
      });

      setRequests(response.data.data.results);
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        "Unable to load your data requests.",
      );

      setRequests([]);

      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setLoading(true);

        const response = await DataCaptureApi.getMine({
          page_size: 100,
        });

        if (active) {
          setRequests(response.data.data.results);
        }
      } catch (error) {
        if (active) {
          const message = getApiErrorMessage(
            error,
            "Unable to load your data requests.",
          );

          setRequests([]);

          toast.error(message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, []);

  /* ========================================================
     SEARCH + STATUS FILTER
  ======================================================== */

  const filteredRequests = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    return requests.filter((request) => {
      const matchesSearch =
        keyword === "" ||
        request.datapoint_label
          .toLowerCase()
          .includes(keyword) ||
        request.datapoint_code
          .toLowerCase()
          .includes(keyword) ||
        request.org_node_name
          .toLowerCase()
          .includes(keyword) ||
        request.reporting_period_name
          .toLowerCase()
          .includes(keyword) ||
        request.module_code
          .toLowerCase()
          .includes(keyword);

      const matchesStatus =
        statusFilter === "All" ||
        request.submission_status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [requests, search, statusFilter]);

  /* ========================================================
     KPI COUNTS
  ======================================================== */

  const kpis = useMemo(() => {
    const draft = requests.filter(
      (request) =>
        request.submission_status === "DRAFT",
    ).length;

    const submitted = requests.filter(
      (request) =>
        request.submission_status === "SUBMITTED",
    ).length;

    const approved = requests.filter(
      (request) =>
        request.submission_status === "APPROVED",
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
      assigned: requests.length,
      draft,
      submitted,
      approved,
      attention,
    };
  }, [requests]);

  /* ========================================================
     ALERTS
  ======================================================== */

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

  /* ========================================================
     TABLE COLUMNS
  ======================================================== */

  const columns = useMemo<
    ColumnDef<DataRequestListItem>[]
  >(
    () => [
      /* ------------------------------------------------------
         DATAPOINT
      ------------------------------------------------------ */

      {
        accessorKey: "datapoint_label",

        header: "Datapoint",

        cell: ({ row }) => {
          const request = row.original;

          return (
            <div className="min-w-[220px] py-1">
              <p className="font-semibold text-[#22243A]">
                {request.datapoint_label}
              </p>

              <p className="mt-1 text-xs text-[#6B7280]">
                {request.datapoint_code}
              </p>
            </div>
          );
        },
      },

      /* ------------------------------------------------------
         ORGANIZATION
      ------------------------------------------------------ */

      {
        accessorKey: "org_node_name",

        header: "Organization",

        cell: ({ row }) => (
          <span className="text-sm text-[#4B5563]">
            {row.original.org_node_name}
          </span>
        ),
      },

      /* ------------------------------------------------------
         REPORTING PERIOD
      ------------------------------------------------------ */

      // {
      //   accessorKey: "reporting_period_name",

      //   header: "Reporting Period",

      //   cell: ({ row }) => (
      //     <span className="text-sm text-[#4B5563]">
      //       {row.original.reporting_period_name}
      //     </span>
      //   ),
      // },

      /* ------------------------------------------------------
         MODULE
      ------------------------------------------------------ */

      // {
      //   accessorKey: "module_code",

      //   header: "Module",

      //   cell: ({ row }) => (
      //     <Badge variant="system">
      //       {formatModule(row.original.module_code)}
      //     </Badge>
      //   ),
      // },

      /* ------------------------------------------------------
         DUE DATE
      ------------------------------------------------------ */

      {
        accessorKey: "due_date",

        header: "Due Date",

        cell: ({ row }) => {
          const dueDate = row.original.due_date;

          if (!dueDate) {
            return (
              <span className="text-sm text-muted-foreground">
                No due date
              </span>
            );
          }

          const overdue =
            new Date(dueDate).getTime() <
              new Date().setHours(0, 0, 0, 0) &&
            row.original.status === "OPEN";

          return (
            <div className="flex items-center gap-2">
              <Clock3
                className={`h-4 w-4 ${
                  overdue
                    ? "text-red-500"
                    : "text-[#6B7280]"
                }`}
              />

              <span
                className={`text-sm ${
                  overdue
                    ? "font-semibold text-red-600"
                    : "text-[#4B5563]"
                }`}
              >
                {formatDate(dueDate)}
              </span>
            </div>
          );
        },
      },

      /* ------------------------------------------------------
         REQUEST STATUS
      ------------------------------------------------------ */

      {
        accessorKey: "status",

        header: "Request",

        cell: ({ row }) => {
          const status = row.original.status;

          return (
            <Badge
              variant={
                status === "OPEN"
                  ? "info"
                  : status === "COMPLETED"
                    ? "success"
                    : "destructive"
              }
            >
              {formatStatus(status)}
            </Badge>
          );
        },
      },

      /* ------------------------------------------------------
         SUBMISSION STATUS
      ------------------------------------------------------ */

      {
        accessorKey: "submission_status",

        header: "Submission",

        cell: ({ row }) => {
          const status =
            row.original.submission_status;

          if (!status) {
            return (
              <span className="text-sm text-muted-foreground">
                Not started
              </span>
            );
          }

          return (
            <Badge variant={getSubmissionVariant(status)}>
              {formatStatus(status)}
            </Badge>
          );
        },
      },

      /* ------------------------------------------------------
         ACTION
      ------------------------------------------------------ */

      {
        id: "actions",

        header: "Action",

        enableSorting: false,

        cell: ({ row }) => (
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              navigate(
                `/data-capture/requests/${row.original.id}`,
              )
            }
          >
            Open
          </Button>
        ),
      },
    ],
    [navigate],
  );

  /* ========================================================
     RENDER
  ======================================================== */

  return (
    <AppShell
  title="Data Capture"
  description="Manage and complete ESG data-capture requests."
>
  <div className="mt-6 space-y-6 py-3">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h2 className="text-lg font-semibold text-[#22243A]">
          Data Requests
        </h2>

        <p className="text-sm text-muted-foreground">
          View requests assigned to you and manage
          authorized data-capture requests.
        </p>
      </div>

      {/* <Button
        type="button"
        onClick={() =>
          navigate("/data-capture/requests/create")
        }
      >
        Create Request
      </Button> */}
    </div>

    {/* existing DataTable / toolbar / cards */}
  </div>

      <div className="space-y-6">
        {/* ==================================================
            KPI CARDS
        ================================================== */}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <KpiCard
            title="Assigned"
            value={kpis.assigned}
            description="Requests assigned to you"
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

      {/* ==================================================
    DUE DATE ALERTS
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
          Keep your assigned requests on schedule.
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
                    ? "One assigned request has passed its due date."
                    : `${alerts.overdue} assigned requests have passed their due dates.`}
                </p>

                <p className="mt-2 text-xs font-medium text-red-600">
                  Please review and complete these requests as soon as
                  possible.
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
                    ? "One assigned request is due within the next 3 days."
                    : `${alerts.dueSoon} assigned requests are due within the next 3 days.`}
                </p>

                <p className="mt-2 text-xs font-medium text-amber-600">
                  Open your requests below to continue your work.
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
            search || statusFilter !== "All"
              ? "No data requests match the selected filters."
              : "No data requests are currently assigned to you."
          }
          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}
            >
              <Select
                value={statusFilter}
                onValueChange={(value) => {
                  setStatusFilter(
                    value as "All" | SubmissionStatus,
                  );
                }}
              >
                <SelectTrigger className="h-9 w-32 shrink-0">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="All">
                    Status
                  </SelectItem>

                  <SelectItem value="DRAFT">
                    Draft
                  </SelectItem>

                  <SelectItem value="SUBMITTED">
                    Submitted
                  </SelectItem>

                  <SelectItem value="APPROVED">
                    Approved
                  </SelectItem>

                  <SelectItem value="REJECTED">
                    Rejected
                  </SelectItem>
                </SelectContent>
              </Select>

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
      className={`overflow-hidden transition-shadow hover:shadow-md ${className ?? ""}`}
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
            className={`shrink-0 rounded-xl p-2.5 ${iconClassName ?? ""}`}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ==========================================================
   FORMATTERS
========================================================== */

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

// function formatModule(value: string) {
//   return value
//     .replace(/_/g, " ")
//     .replace(/\b\w/g, (character) =>
//       character.toUpperCase(),
//     );
// }

function formatStatus(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

function getSubmissionVariant(
  status: SubmissionStatus,
): "info" | "success" | "destructive" | "warning" | "outline" {
  switch (status) {
    case "DRAFT":
      return "warning";

    case "SUBMITTED":
      return "info";

    case "APPROVED":
      return "success";

    case "REJECTED":
      return "destructive";

    default:
      return "outline";
  }
}