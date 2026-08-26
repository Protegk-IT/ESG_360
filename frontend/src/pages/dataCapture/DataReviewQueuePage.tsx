import { useCallback, useEffect, useMemo, useState } from "react";

import {
  AlertCircle,
  FileCheck2,
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
import { getApiErrorMessage } from "@/services/errors";

import type {
  DataRequestListItem,
  SubmissionStatus,
} from "@/types/dataCapture";

import type { ColumnDef } from "@tanstack/react-table";

/* ==========================================================
   REVIEW QUEUE
   ----------------------------------------------------------
   Route: /data-capture/review  (data.approve only)

   Backed by the same scoped `requests/` listing the manager
   screen uses — visibility (which requests this reviewer can
   even see) is entirely backend-authoritative via
   readable_request_queryset. This page only decides which
   *subset* of that visible set to default-show: submissions
   actually waiting on this reviewer.
========================================================== */

const REVIEW_STATUS_OPTIONS: Array<"All" | SubmissionStatus> = [
  "SUBMITTED",
  "All",
  "APPROVED",
  "REJECTED",
  "DRAFT",
];

export default function DataReviewQueuePage() {
  const navigate = useNavigate();

  const [requests, setRequests] = useState<DataRequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<"All" | SubmissionStatus>("All");

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);

      const response = await DataCaptureApi.getAll({ page_size: 100 });
      setRequests(response.data.data?.results ?? []);
    } catch (error) {
      toast.error(
        getApiErrorMessage(error, "Unable to load requests for review."),
      );
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      if (active) await loadRequests();
    })();
    return () => {
      active = false;
    };
  }, [loadRequests]);

  const filteredRequests = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    return requests.filter((request) => {
      const matchesSearch =
        keyword === "" ||
        request.datapoint_label.toLowerCase().includes(keyword) ||
        request.datapoint_code.toLowerCase().includes(keyword) ||
        request.org_node_name.toLowerCase().includes(keyword) ||
        request.assignee_username.toLowerCase().includes(keyword);

      const matchesStatus =
        statusFilter === "All" ||
        request.submission_status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [requests, search, statusFilter]);

  const kpis = useMemo(() => {
    const pending = requests.filter(
      (r) => r.submission_status === "SUBMITTED",
    ).length;
    const approved = requests.filter(
      (r) => r.submission_status === "APPROVED",
    ).length;
    const rejected = requests.filter(
      (r) => r.submission_status === "REJECTED",
    ).length;

    return { pending, approved, rejected };
  }, [requests]);

  const columns = useMemo<ColumnDef<DataRequestListItem>[]>(
    () => [
      {
        accessorKey: "datapoint_label",
        header: "Datapoint",
        cell: ({ row }) => (
          <div className="min-w-[220px] py-1">
            <p className="font-semibold text-[#22243A]">
              {row.original.datapoint_label}
            </p>
            <p className="mt-1 text-xs text-[#6B7280]">
              {row.original.datapoint_code}
            </p>
          </div>
        ),
      },
      { accessorKey: "org_node_name", header: "Organization / Site" },
      { accessorKey: "assignee_username", header: "Submitted By" },
      {
        accessorKey: "submission_status",
        header: "Status",
        cell: ({ row }) => {
          const status = row.original.submission_status;
          if (!status) {
            return (
              <span className="text-sm text-muted-foreground">
                Not started
              </span>
            );
          }
          const variant =
            status === "SUBMITTED"
              ? "info"
              : status === "APPROVED"
                ? "success"
                : status === "REJECTED"
                  ? "destructive"
                  : "warning";
          return <Badge variant={variant}>{formatStatus(status)}</Badge>;
        },
      },
      {
        id: "actions",
        header: () => <div className="text-right">Review</div>,
        cell: ({ row }) => (
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                navigate(`/data-capture/requests/${row.original.id}`)
              }
            >
              Open
            </Button>
          </div>
        ),
      },
    ],
    [navigate],
  );

  return (
    <AppShell
      title="Review Requests"
      description="Inspect submitted work and approve, reject, or reopen it."
    >
      <div className="mt-6 space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <KpiCard
            title="Pending Review"
            value={kpis.pending}
            description="Submitted, awaiting your decision"
            icon={FileCheck2}
            className="border-violet-200 bg-violet-50/60"
            iconClassName="bg-violet-100 text-violet-600"
          />
          <KpiCard
            title="Approved"
            value={kpis.approved}
            description="Already approved"
            icon={FileCheck2}
            className="border-emerald-200 bg-emerald-50/60"
            iconClassName="bg-emerald-100 text-emerald-600"
          />
          <KpiCard
            title="Rejected"
            value={kpis.rejected}
            description="Sent back for correction"
            icon={AlertCircle}
            className="border-rose-200 bg-rose-50/60"
            iconClassName="bg-rose-100 text-rose-600"
          />
        </div>

        <DataTable
          columns={columns}
          data={filteredRequests}
          loading={loading}
          emptyMessage={
            statusFilter === "SUBMITTED"
              ? "Nothing is waiting on your review right now."
              : "No requests match the selected filters."
          }
          toolbar={
            <DataTableToolbar search={search} onSearchChange={setSearch}>
              <Select
                value={statusFilter}
                onValueChange={(value) =>
                  setStatusFilter(value as "All" | SubmissionStatus)
                }
              >
                <SelectTrigger className="h-9 w-36 shrink-0">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  {REVIEW_STATUS_OPTIONS.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option === "All" ? "All statuses" : formatStatus(option)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                size="sm"
                onClick={() => void loadRequests()}
                disabled={loading}
                className="h-9 shrink-0"
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
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

function KpiCard({
  title,
  value,
  description,
  icon: Icon,
  className,
  iconClassName,
}: {
  title: string;
  value: number;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  className?: string;
  iconClassName?: string;
}) {
  return (
    <Card className={`overflow-hidden transition-shadow hover:shadow-md ${className ?? ""}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-[#6B7280]">{title}</p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-[#22243A]">
              {value}
            </p>
            <p className="mt-1 text-xs leading-5 text-[#6B7280]">
              {description}
            </p>
          </div>
          <div className={`shrink-0 rounded-xl p-2.5 ${iconClassName ?? ""}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function formatStatus(value: string) {
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}