import { useEffect, useState, type ComponentType } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  FileText,
  Loader2,
  MapPin,
  RefreshCw,
  User,
  UserCog,
} from "lucide-react";

import DataCaptureApi from "@/api/dataCapture/DataCaptureApi";
import UserApi from "@/api/users/UserApi";

import { getApiErrorMessage } from "@/services/errors";
import type {
  DataRequestDetail,
  SubmissionStatus,
} from "@/types/dataCapture";

interface AssigneeOption {
  id: string;
  username: string;
  full_name?: string;
}

type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "info"
  | "warning";

function submissionStatusBadge(
  status: SubmissionStatus | null,
): {
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

function formatDateTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function DetailItem({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex min-w-0 gap-3">
      <div className="mt-0.5 shrink-0 rounded-md bg-[#E8F4F2] p-2">
        <Icon className="h-4 w-4 text-[#1F766D]" />
      </div>

      <div className="min-w-0 space-y-1">
        <Label className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          {label}
        </Label>

        <p className="break-words text-sm font-medium leading-5 text-[#22243A]">
          {value}
        </p>
      </div>
    </div>
  );
}

function MetaItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0 space-y-1">
      <Label className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
        {label}
      </Label>

      <p className="break-words text-sm text-[#22243A]">
        {value}
      </p>
    </div>
  );
}

export default function DataRequestManageDetailPage() {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();

  const [request, setRequest] = useState<DataRequestDetail | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [reassignDialogOpen, setReassignDialogOpen] = useState(false);

  const [assignees, setAssignees] = useState<AssigneeOption[]>([]);
  const [loadingAssignees, setLoadingAssignees] = useState(false);

  const [selectedAssignee, setSelectedAssignee] = useState("");
  const [reassignReason, setReassignReason] = useState("");

  const [reassigning, setReassigning] = useState(false);

  const loadRequest = async (
    mode: "initial" | "refresh" = "refresh",
  ) => {
    if (!requestId) {
      setError("Data request ID is missing.");
      setLoading(false);
      return;
    }

    try {
      if (mode === "initial") {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);

      const response = await DataCaptureApi.getById(requestId);

      const data = response.data.data;

      if (!data) {
        throw new Error(
          "Data request response did not contain request data.",
        );
      }

      setRequest(data);
    } catch (requestError) {
      const message = getApiErrorMessage(
        requestError,
        "Unable to load this data request.",
      );

      setError(message);

      if (mode === "refresh") {
        toast.error(message);
      }
    } finally {
      if (mode === "initial") {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  };

  useEffect(() => {
    let ignore = false;

    Promise.resolve().then(() => {
      if (!ignore) {
        void loadRequest("initial");
      }
    });

    return () => {
      ignore = true;
    };

    // loadRequest uses requestId as its source of truth.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

  const openReassignDialog = async () => {
    setSelectedAssignee(request?.assignee ?? "");
    setReassignReason("");
    setReassignDialogOpen(true);

    try {
      setLoadingAssignees(true);

      const response = await UserApi.getAll();

      setAssignees(
        (response.data ?? []).map((user) => ({
          id: String(user.id),
          username: user.username,
          full_name: user.full_name,
        })),
      );
    } catch (assigneeError) {
      console.error(
        "Failed to load assignable users:",
        assigneeError,
      );

      toast.error(
        getApiErrorMessage(
          assigneeError,
          "Failed to load assignee list.",
        ),
      );
    } finally {
      setLoadingAssignees(false);
    }
  };

  const handleReassign = async () => {
    if (!requestId || !selectedAssignee) {
      return;
    }

    try {
      setReassigning(true);

      await DataCaptureApi.reassign(requestId, {
        assignee: selectedAssignee,
        reason: reassignReason || undefined,
      });

      await loadRequest("refresh");

      setReassignDialogOpen(false);

      toast.success("Request reassigned successfully.");
    } catch (reassignError) {
      toast.error(
        getApiErrorMessage(
          reassignError,
          "Unable to reassign this request.",
        ),
      );
    } finally {
      setReassigning(false);
    }
  };

  if (loading) {
    return (
      <AppShell
        title="Manage Request"
        description="Loading request..."
      >
        <div className="space-y-5">
          <div className="h-9 w-72 animate-pulse rounded-lg bg-muted" />

          <div className="h-44 animate-pulse rounded-xl bg-muted" />

          <div className="grid gap-4 md:grid-cols-2">
            <div className="h-40 animate-pulse rounded-xl bg-muted" />
            <div className="h-40 animate-pulse rounded-xl bg-muted" />
          </div>
        </div>
      </AppShell>
    );
  }

  if (error || !request) {
    return (
      <AppShell
        title="Manage Request"
        description="Unable to load this request."
      >
        <div className="space-y-5">
          <Button
            variant="ghost"
            className="-ml-3 w-fit"
            onClick={() => navigate("/data-capture/manage")}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Manage Requests
          </Button>

          <Alert variant="destructive">
            <AlertTitle>Unable to load request</AlertTitle>

            <AlertDescription>
              {error ??
                "The requested data request could not be found."}
            </AlertDescription>
          </Alert>
        </div>
      </AppShell>
    );
  }

  const { label, variant } = submissionStatusBadge(
    request.submission?.status ?? null,
  );

  const dueDate = request.due_date
    ? formatDate(request.due_date)
    : "No due date";

  return (
    <AppShell
      title="Manage Request"
      description="Review request details, assignment, and current progress."
    >
      <div className="space-y-5 ">
        {/* ======================================================
            PAGE ACTIONS
        ====================================================== */}

        <div className="flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between ">
          <Button
            variant="ghost"
            className="-ml-3 w-fit"
            onClick={() =>
              navigate("/data-capture/manage")
            }
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Manage Requests
          </Button>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                void loadRequest("refresh")
              }
              disabled={refreshing}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${
                  refreshing ? "animate-spin" : ""
                }`}
              />
              Refresh
            </Button>

            <Button
              type="button"
              onClick={() =>
                void openReassignDialog()
              }
            >
              <UserCog className="mr-2 h-4 w-4" />
              Reassign
            </Button>
          </div>
        </div>

        {/* ======================================================
            REQUEST HEADER
        ====================================================== */}

        <Card className="overflow-hidden border shadow-sm ">
          <div className="bg-gradient-to-r from-[#22243A] via-[#303456] to-[#1F766D] px-5 py-6 text-white sm:px-7 sm:py-7">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant="outline"
                    className="border-white/20 bg-white/10 text-white"
                  >
                    {request.datapoint.data_type}
                  </Badge>

                  <Badge variant={variant}>
                    {label}
                  </Badge>

                  <Badge
                    variant="outline"
                    className="border-white/20 bg-white/10 text-white"
                  >
                    {request.status}
                  </Badge>
                </div>

                <div className="mt-4">
                  <h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">
                    {request.datapoint.label}
                  </h1>

                  <p className="mt-2 font-mono text-sm text-white/65">
                    {request.datapoint.code}
                  </p>
                </div>
              </div>

              <div className="shrink-0 rounded-lg border border-white/10 bg-white/10 px-4 py-3">
                <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-white/60">
                  Submission Status
                </p>

                <p className="mt-1 text-sm font-semibold text-white">
                  {label}
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* ======================================================
            REQUEST DETAILS
        ====================================================== */}

        <Card>
          <CardHeader className="pb-4 px-4">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <ClipboardList className="h-4 w-4 text-[#1F766D]" />
              Request Details
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-6 px-4">
            <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
              <DetailItem
                icon={MapPin}
                label="Organization / Site"
                value={request.org_node_name}
              />

              <DetailItem
                icon={CalendarDays}
                label="Reporting Period"
                value={request.reporting_period_name}
              />

              <DetailItem
                icon={User}
                label="Assigned To"
                value={request.assignee_username}
              />

              <DetailItem
                icon={Clock3}
                label="Due Date"
                value={dueDate}
              />
            </div>

            <div className=" pt-5">
              <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
                <MetaItem
                  label="Module"
                  value={
                    request.module_code || "—"
                  }
                />

                <MetaItem
                  label="Requested By"
                  value={request.requested_by || "—"}
                />

                <MetaItem
                  label="Created"
                  value={formatDateTime(
                    request.created_at,
                  )}
                />

                <MetaItem
                  label="Last Updated"
                  value={formatDateTime(
                    request.updated_at,
                  )}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ======================================================
            ASSIGNMENT / STATUS SUMMARY
        ====================================================== */}

        <Card>
          <CardContent className="px-5 py-5 sm:px-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-start gap-3">
                <div className="rounded-md bg-[#E8F4F2] p-2">
                  <ClipboardCheck className="h-4 w-4 text-[#1F766D]" />
                </div>

                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[#22243A]">
                    Current assignment
                  </p>

                  <p className="mt-1 text-sm text-muted-foreground">
                    Assigned to{" "}
                    <span className="font-medium text-[#22243A]">
                      {request.assignee_username}
                    </span>
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 sm:justify-end">
                <Badge variant="outline">
                  {request.status}
                </Badge>

                <Badge variant={variant}>
                  {label}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ======================================================
            INSTRUCTIONS
        ====================================================== */}

        {request.instructions && (
          <Card>
            <CardHeader className="pb-4 px-4">
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <FileText className="h-4 w-4 text-[#1F766D]" />
                Instructions
              </CardTitle>
            </CardHeader>

            <CardContent className="px-4">
              <div className="rounded-lg border bg-muted/20 px-4 py-3.5">
                <p className="whitespace-pre-wrap text-sm leading-6 text-[#4B5563]">
                  {request.instructions}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ======================================================
            ACTIVE REQUEST NOTICE
        ====================================================== */}

        <Alert className="border-[#B9DED7] bg-[#F1F9F7]">
          <CheckCircle2 className="text-[#1F766D]" />

          <AlertTitle className="text-[#184F4A]">
            Request is active
          </AlertTitle>

          <AlertDescription className="text-[#35645F]">
            This request is assigned to{" "}
            <strong className="font-semibold text-[#184F4A]">
              {request.assignee_username}
            </strong>
            . Any lifecycle or permission restrictions remain
            enforced by the backend.
          </AlertDescription>
        </Alert>
      </div>

      {/* ======================================================
          REASSIGN DIALOG
      ====================================================== */}

      <Dialog
        open={reassignDialogOpen}
        onOpenChange={(open) => {
          if (!reassigning) {
            setReassignDialogOpen(open);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Reassign Request
            </DialogTitle>

            <DialogDescription>
              Move this request to a different assignee.
              The current progress, if any, stays intact.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-1">
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                New Assignee
              </Label>

              <Select
                value={selectedAssignee}
                onValueChange={
                  setSelectedAssignee
                }
                disabled={loadingAssignees || reassigning}
              >
                <SelectTrigger className="h-10">
                  <SelectValue
                    placeholder={
                      loadingAssignees
                        ? "Loading assignees..."
                        : "Select assignee"
                    }
                  />
                </SelectTrigger>

                <SelectContent>
                  {assignees.map((user) => (
                    <SelectItem
                      key={user.id}
                      value={user.id}
                    >
                      {user.full_name ||
                        user.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium">
                Reason{" "}
                <span className="font-normal text-muted-foreground">
                  (optional)
                </span>
              </Label>

              <Textarea
                rows={4}
                placeholder="Why is this request being reassigned?"
                value={reassignReason}
                onChange={(event) =>
                  setReassignReason(
                    event.target.value,
                  )
                }
                disabled={reassigning}
                className="resize-none"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                setReassignDialogOpen(false)
              }
              disabled={reassigning}
            >
              Cancel
            </Button>

            <Button
              type="button"
              onClick={() =>
                void handleReassign()
              }
              disabled={
                reassigning ||
                loadingAssignees ||
                !selectedAssignee ||
                selectedAssignee ===
                  request.assignee
              }
            >
              {reassigning && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Reassign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}