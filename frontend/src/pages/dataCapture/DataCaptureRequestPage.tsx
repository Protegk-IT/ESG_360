import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ComponentType,
} from "react";

import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  Check,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  Download,
  FileText,
  History,
  MapPin,
  Paperclip,
  RefreshCw,
  RotateCcw,
  Save,
  Send,
  Trash2,
  Upload,
  User,
  X,
  XCircle,
} from "lucide-react";

import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import axios from "axios";

import AppShell from "@/components/layout/AppShell";
import ConfirmDialog from "@/common/ConfirmDialog";
import ReasonDialog from "./ReasonDialog";

import { DynamicFieldRenderer } from "@/pages/datapoints/DynamicFieldRenderer";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";

import DataCaptureApi from "@/api/dataCapture/DataCaptureApi";

import type {
  DataRequestDetail,
  EvidenceFile,
  SubmissionHistory,
  SubmissionStatus,
} from "@/types/dataCapture";

import DatapointApi from "@/api/datapoints/DatapointApi";
import type { DatapointDetail, Unit } from "@/types/datapoint";

import type { FieldValue } from "@/pages/datapoints/fields";
import type { TableAnswerDraft } from "@/pages/datapoints/tableAnswerAdapter";

import {
  answerToFieldValue,
  fieldValueToAnswerPayload,
} from "@/pages/dataCapture/scalarAnswerAdapter";

import {
  hydrateTableDraft,
  tableDraftToRowPayloads,
} from "@/pages/dataCapture/tableAnswerAdapter";

import { useDataCaptureAccess } from "@/pages/dataCapture/useDataCaptureAccess";

import { getApiErrorMessage } from "@/services/errors";

const MAX_EVIDENCE_FILE_SIZE = 10 * 1024 * 1024;

const SUPPORTED_EVIDENCE_ACCEPT =
  ".pdf,.jpg,.jpeg,.png,.csv,.xlsx,application/pdf,image/jpeg,image/png,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

const SUPPORTED_EVIDENCE_EXTENSIONS = new Set([
  "pdf",
  "jpg",
  "jpeg",
  "png",
  "csv",
  "xlsx",
]);

function isSupportedEvidenceFile(file: File): boolean {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return SUPPORTED_EVIDENCE_EXTENSIONS.has(extension);
}

/* ==========================================================
   FIELD-LEVEL ERROR PARSING
   ----------------------------------------------------------
   DRF ValidationError on TypedValueWriteSerializer / cell
   writes returns { field_name: ["message", ...], ... } in the
   response body. This surfaces those per-field so the maker
   sees exactly what's wrong instead of one generic toast —
   matching the MD requirement to "surface field/table errors
   in a useful way." Falls back silently to the existing
   getApiErrorMessage toast if the shape doesn't match (e.g.
   PermissionDenied's { detail: "..." }).

   NOTE: written independently of services/errors.ts since
   that file wasn't available — worth consolidating there if
   its shape already covers this.
========================================================== */

function parseFieldErrors(error: unknown): Record<string, string> | null {
  if (!axios.isAxiosError(error)) return null;

  const body = error.response?.data;
  if (!body || typeof body !== "object") return null;

  // Unwrap the shared { success, message, data } envelope if the
  // error body happens to be wrapped in it; otherwise use as-is.
  const candidate =
    "data" in body && typeof (body as Record<string, unknown>).data === "object"
      ? (body as Record<string, unknown>).data
      : body;

  if (!candidate || typeof candidate !== "object") return null;

  const entries = Object.entries(candidate as Record<string, unknown>).filter(
    ([key, val]) =>
      key !== "success" &&
      key !== "message" &&
      key !== "detail" &&
      (Array.isArray(val) || typeof val === "string"),
  );

  if (entries.length === 0) return null;

  return Object.fromEntries(
    entries.map(([key, val]) => [
      key,
      Array.isArray(val) ? val.join(" ") : String(val),
    ]),
  );
}

/* ==========================================================
   PAGE
========================================================== */

export default function DataCaptureRequestPage() {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();

  /* ========================================================
     REQUEST
  ======================================================== */

  const [request, setRequest] = useState<DataRequestDetail | null>(null);
  const access = useDataCaptureAccess(request);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [datapoint, setDatapoint] = useState<DatapointDetail | null>(null);
  const [unitsById, setUnitsById] = useState<Record<string, Unit>>({});

  /* ========================================================
     ANSWER
  ======================================================== */

  const [value, setValue] = useState<FieldValue>(null);
  const [answerUnit, setAnswerUnit] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string> | null>(
    null,
  );

  const [persistedTableRowIds, setPersistedTableRowIds] = useState<Set<string>>(
    new Set(),
  );

  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  /* ========================================================
     EVIDENCE
  ======================================================== */

  const [evidence, setEvidence] = useState<EvidenceFile[]>([]);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [uploadingEvidence, setUploadingEvidence] = useState(false);
  const [evidenceToDelete, setEvidenceToDelete] =
    useState<EvidenceFile | null>(null);
  const [deletingEvidence, setDeletingEvidence] = useState(false);

  const evidenceInputRef = useRef<HTMLInputElement | null>(null);

  /* ========================================================
     HISTORY
  ======================================================== */

  const [history, setHistory] = useState<SubmissionHistory | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  /* ========================================================
     REVIEWER ACTIONS
  ======================================================== */

  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reopening, setReopening] = useState(false);

  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [reopenDialogOpen, setReopenDialogOpen] = useState(false);

  /* ========================================================
     LOAD REQUEST
  ======================================================== */

  const loadRequest = useCallback(
    async (mode: "initial" | "refresh" = "refresh") => {
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

        const datapointResponse = await DatapointApi.getById(
          data.datapoint.id,
        );

        // Replace the single-family fetch in loadRequest() with this:

const resolvedDatapoint = datapointResponse.data;

// Collect every distinct unit_family referenced anywhere this datapoint
// needs units resolved for: the datapoint's own family (scalar fields)
// AND each TABLE column's own family, which is independent and may
// differ from the parent datapoint's family entirely.
const familyIds = new Set<string>();

const ownFamilyId = resolveUnitFamilyId(resolvedDatapoint);
if (ownFamilyId) familyIds.add(ownFamilyId);

for (const column of resolvedDatapoint.table_columns ?? []) {
  if (column.unit_family) familyIds.add(column.unit_family);
}

const unitLists = await Promise.all(
  Array.from(familyIds).map((familyId) =>
    DatapointApi.getUnitsByFamily(familyId).then((res) => res.data),
  ),
);

const mergedUnitsById = Object.fromEntries(
  unitLists.flat().map((unit) => [String(unit.id), unit]),
);

setUnitsById(mergedUnitsById);
setRequest(data);
setDatapoint(resolvedDatapoint);
hydrateAnswer(data, resolvedDatapoint, setValue, setAnswerUnit, setPersistedTableRowIds);
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
    },
    [requestId],
  );

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
  }, [loadRequest]);

  /* ========================================================
     LOAD EVIDENCE
  ======================================================== */

  useEffect(() => {
    let ignore = false;

    const loadEvidence = async () => {
      if (!requestId || !request) {
        return;
      }

      if (!request.submission || !access.canViewEvidence) {
        if (!ignore) {
          setEvidence([]);
          setEvidenceLoading(false);
        }
        return;
      }

      try {
        setEvidenceLoading(true);

        const response = await DataCaptureApi.getEvidence(requestId, {
          page_size: 100,
        });

        if (!ignore) {
          const payload = unwrapApiData(response.data) as { results?: EvidenceFile[] };
          setEvidence(payload?.results ?? []);
        }
      } catch (evidenceError) {
        if (!ignore) {
          toast.error(
            getApiErrorMessage(evidenceError, "Unable to load evidence."),
          );
          setEvidence([]);
        }
      } finally {
        if (!ignore) {
          setEvidenceLoading(false);
        }
      }
    };

    void loadEvidence();

    return () => {
      ignore = true;
    };
  }, [request, requestId, access.canViewEvidence]);

  /* ========================================================
     LOAD HISTORY
  ======================================================== */

  useEffect(() => {
    let ignore = false;

    const loadHistory = async () => {
      if (!requestId || !request) {
        return;
      }

      if (!request.submission) {
        if (!ignore) {
          setHistory(null);
          setHistoryLoading(false);
        }
        return;
      }

      try {
        setHistoryLoading(true);

        const response = await DataCaptureApi.getHistory(requestId);

        if (!ignore) {
          const payload = unwrapApiData<SubmissionHistory>(response.data);
          setHistory(payload);
        }
      } catch (historyError) {
        if (!ignore) {
          toast.error(
            getApiErrorMessage(
              historyError,
              "Unable to load request history.",
            ),
          );
          setHistory(null);
        }
      } finally {
        if (!ignore) {
          setHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      ignore = true;
    };
  }, [request, requestId]);

  /* ========================================================
     DERIVED STATE / ACCESS
  ======================================================== */

  const submissionStatus = request?.submission?.status ?? null;

  const editable = submissionStatus === "DRAFT" && access.canEnter;

  const canApproveAction = submissionStatus === "SUBMITTED" && access.canApprove;
  const canRejectAction = submissionStatus === "SUBMITTED" && access.canReject;
  const canReopenAction = submissionStatus === "REJECTED" && access.canReopen;
  const canSubmitAction = editable && access.canSubmitDraft;

  const dueDateState = useMemo(
    () => getDueDateState(request?.due_date ?? null),
    [request?.due_date],
  );

  const backDestination = useMemo(() => {
    if (access.canEnter || access.canSubmitDraft) {
      return { url: "/data-capture", label: "Back to My Requests" };
    }
    if (access.canApprove || access.canReject || access.canReopen) {
      return { url: "/data-capture/review", label: "Back to Review Requests" };
    }
    if (access.canManage) {
      return { url: "/data-capture/manage", label: "Back to Manage Requests" };
    }
    return { url: "/data-capture", label: "Back to Data Capture" };
  }, [access]);

  /* ========================================================
     SAVE DRAFT
  ======================================================== */

  const handleSaveDraft = async () => {
    if (!request || !requestId) return;

    if (!editable) {
      toast.error("This submission is no longer editable.");
      return;
    }

    setFieldErrors(null);

   try {
  setSaving(true);

  if (request.datapoint.data_type === "TABLE") {
    if (Array.isArray(value)) {
      await saveTableRows(requestId, value, persistedTableRowIds);
    }
  } else {
    await DataCaptureApi.saveAnswer(
      requestId,
      fieldValueToAnswerPayload(request.datapoint.data_type, value, answerUnit),
    );
  }

  await loadRequest("refresh");
  toast.success("Draft saved.");
} catch (saveError) {
  // Resync even on failure — otherwise a retry re-attempts CREATE on
  // rows that a partial success already persisted, causing the same
  // IntegrityError again.
  await loadRequest("refresh");

  const parsed = parseFieldErrors(saveError);
  if (parsed) {
    setFieldErrors(parsed);
    toast.error("Some fields need attention before this draft can be saved.");
  } else {
    toast.error(getApiErrorMessage(saveError, "Unable to save the draft."));
  }
} finally {
  setSaving(false);
}
  };

  /* ========================================================
     SUBMIT
  ======================================================== */

 const handleSubmit = async () => {
  if (!request || !requestId) return;

  if (!canSubmitAction) {
    toast.error("You don't have permission to submit this request.");
    return;
  }
    setFieldErrors(null);

    try {
      setSubmitting(true);

      if (request.datapoint.data_type === "TABLE") {
        if (Array.isArray(value)) {
          await saveTableRows(requestId, value, persistedTableRowIds);
        }
      } else {
        await DataCaptureApi.saveAnswer(
          requestId,
          fieldValueToAnswerPayload(
            request.datapoint.data_type,
            value,
            answerUnit,
          ),
        );
      }

      await DataCaptureApi.submit(requestId);
      await loadRequest("refresh");
      toast.success("Submission sent for review.");
    } catch (submitError) {
      const parsed = parseFieldErrors(submitError);
      if (parsed) {
        setFieldErrors(parsed);
        toast.error("Some fields need attention before this can be submitted.");
      } else {
        toast.error(
          getApiErrorMessage(submitError, "Unable to submit this request."),
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  /* ========================================================
     REVIEWER ACTIONS
  ======================================================== */

  const handleApprove = async () => {
    if (!requestId) return;

    if (!canApproveAction) {
      toast.error("You don't have permission to approve this submission.");
      return;
    }

    try {
      setApproving(true);
      await DataCaptureApi.approve(requestId);
      await loadRequest("refresh");
      toast.success("Submission approved.");
    } catch (approveError) {
      toast.error(
        getApiErrorMessage(approveError, "Unable to approve this submission."),
      );
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async (reason: string) => {
    if (!requestId) return;

    if (!canRejectAction) {
      toast.error("You don't have permission to reject this submission.");
      return;
    }

    try {
      setRejecting(true);
      await DataCaptureApi.reject(requestId, { reason });
      await loadRequest("refresh");
      setRejectDialogOpen(false);
      toast.success("Submission rejected.");
    } catch (rejectError) {
      toast.error(
        getApiErrorMessage(rejectError, "Unable to reject this submission."),
      );
    } finally {
      setRejecting(false);
    }
  };

  const handleReopen = async (reason: string) => {
    if (!requestId) return;

    if (!canReopenAction) {
      toast.error("You don't have permission to reopen this submission.");
      return;
    }

    try {
      setReopening(true);
      await DataCaptureApi.reopen(requestId, { reason });
      await loadRequest("refresh");
      setReopenDialogOpen(false);
      toast.success("Submission reopened for editing.");
    } catch (reopenError) {
      toast.error(
        getApiErrorMessage(reopenError, "Unable to reopen this submission."),
      );
    } finally {
      setReopening(false);
    }
  };

  /* ========================================================
     EVIDENCE UPLOAD
  ======================================================== */

  const handleEvidenceButtonClick = () => {
    if (uploadingEvidence) return;
    evidenceInputRef.current?.click();
  };

 const handleEvidenceUpload = async (
  event: ChangeEvent<HTMLInputElement>,
) => {
  const file = event.target.files?.[0];

  if (!file || !requestId) {
    event.target.value = "";
    return;
  }

  if (!editable || !access.canUploadEvidence) {
    event.target.value = "";
    toast.error(
      "You don't have permission to add evidence here.",
    );
    return;
  }

  if (file.size > MAX_EVIDENCE_FILE_SIZE) {
    event.target.value = "";
    toast.error(
      "Evidence files must be 10 MB or smaller.",
    );
    return;
  }

  if (!isSupportedEvidenceFile(file)) {
    event.target.value = "";
    toast.error(
      "Unsupported file type. Use PDF, JPEG, PNG, CSV, or XLSX.",
    );
    return;
  }

  try {
    setUploadingEvidence(true);

    const formData = new FormData();

    formData.append("file", file);

    if (request?.submission?.answer?.id) {
      formData.append(
        "answer",
        request.submission.answer.id,
      );
    }

    // Temporary verification
    console.log(
      "Evidence upload:",
      formData.get("file"),
      formData.get("answer"),
    );

    const response =
      await DataCaptureApi.uploadEvidence(
        requestId,
        formData,
      );

    const uploadedEvidence =
      unwrapApiData<EvidenceFile>(
        response.data,
      );

    setEvidence((current) => [
      uploadedEvidence,
      ...current,
    ]);

    toast.success(
      "Evidence uploaded successfully.",
    );
  } catch (uploadError) {
    console.error(
      "Evidence upload failed:",
      uploadError,
    );

    toast.error(
      getApiErrorMessage(
        uploadError,
        "Unable to upload evidence.",
      ),
    );
  } finally {
    setUploadingEvidence(false);

    // Allow selecting the same file again.
    event.target.value = "";
  }
};

  /* ========================================================
     EVIDENCE DOWNLOAD
  ======================================================== */

  const handleEvidenceDownload = async (item: EvidenceFile) => {
    if (!requestId) return;

    if (!access.canViewEvidence) {
      toast.error("You don't have permission to view evidence.");
      return;
    }

    try {
      const response = await DataCaptureApi.downloadEvidence(
        requestId,
        item.id,
      );

      const blob = response.data;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = item.original_filename;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      toast.error(
        getApiErrorMessage(downloadError, "Unable to download evidence."),
      );
    }
  };

  /* ========================================================
     EVIDENCE DELETE
  ======================================================== */

  const handleEvidenceDelete = async () => {
    if (!requestId || !evidenceToDelete) return;

    if (!editable || !access.canDeleteEvidence) {
      toast.error("You don't have permission to delete evidence here.");
      setEvidenceToDelete(null);
      return;
    }

    try {
      setDeletingEvidence(true);

      await DataCaptureApi.deleteEvidence(requestId, evidenceToDelete.id);

      setEvidence((current) =>
        current.filter((entry) => entry.id !== evidenceToDelete.id),
      );

      setEvidenceToDelete(null);
      toast.success("Evidence deleted.");
    } catch (deleteError) {
      toast.error(
        getApiErrorMessage(deleteError, "Unable to delete evidence."),
      );
    } finally {
      setDeletingEvidence(false);
    }
  };

  /* ========================================================
     LOADING
  ======================================================== */

  if (loading) {
    return (
      <AppShell title="Data Capture" description="Loading request...">
        <div className="space-y-4">
          <div className="h-24 animate-pulse rounded-xl bg-muted" />
          <div className="grid gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-16 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
          <div className="h-32 animate-pulse rounded-lg bg-muted" />
          <div className="h-56 animate-pulse rounded-lg bg-muted" />
        </div>
      </AppShell>
    );
  }

  /* ========================================================
     ERROR
  ======================================================== */

  if (error || !request) {
    return (
      <AppShell
        title="Data Capture"
        description="Review and complete the data request."
      >
        <div className="space-y-4">
          <Button variant="ghost" size="sm" onClick={() => navigate("/data-capture")}>
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back to Data Capture
          </Button>

          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Unable to load request</AlertTitle>
            <AlertDescription>
              {error ?? "The requested data request could not be found."}
            </AlertDescription>
          </Alert>
        </div>
      </AppShell>
    );
  }

  /* ========================================================
     RENDER
  ======================================================== */

  return (
    <AppShell
      title="Data Capture"
      description="Review the request, enter data, attach evidence, and complete the workflow."
    >
      <div className="space-y-4">
        {/* TOP ACTIONS */}
        <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2 w-fit text-[#4B5563] hover:bg-[#E8F4F2] hover:text-[#1F766D]"
            onClick={() => navigate(backDestination.url)}
          >
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            {backDestination.label}
          </Button>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void loadRequest("refresh")}
              disabled={refreshing}
            >
              <RefreshCw
                className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>

            {editable && (
  <Button
    variant="outline"
    size="sm"
    onClick={() => void handleSaveDraft()}
    disabled={saving || submitting}
  >
    <Save className="mr-1.5 h-3.5 w-3.5" />
    {saving ? "Saving..." : "Save Draft"}
  </Button>
)}

{canSubmitAction && (
  <Button
    size="sm"
    className="bg-[#1F766D] hover:bg-[#195e57]"
    onClick={() => void handleSubmit()}
    disabled={saving || submitting}
  >
    <Send className="mr-1.5 h-3.5 w-3.5" />
    {submitting ? "Submitting..." : "Submit"}
  </Button>
)}
          </div>
        </div>

        {/* HERO HEADER */}
        <Card className="overflow-hidden border-0 shadow-sm">
          <div className="bg-gradient-to-r from-[#22243A] via-[#303456] to-[#1F766D] px-5 py-5 text-white sm:px-6 sm:py-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className="border-white/25 bg-white/10 text-[11px] text-white"
                  >
                    {formatDataType(request.datapoint.data_type)}
                  </Badge>

                  <SubmissionBadge
                    status={submissionStatus}
                    requestStatus={request.status}
                  />
                </div>

                <h1 className="mt-2.5 text-xl font-bold tracking-tight sm:text-2xl">
                  {request.datapoint.label}
                </h1>

                <p className="mt-1 font-mono text-xs text-white/60">
                  {request.datapoint.code}
                </p>
              </div>

              <div className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-white/10 px-3.5 py-2.5">
                <ClipboardCheck className="h-4 w-4 text-emerald-200" />
                <div>
                  <p className="text-[11px] text-white/60">Submission</p>
                  <p className="text-sm font-semibold">
                    {submissionStatus
                      ? formatStatus(submissionStatus)
                      : "Not started"}
                  </p>
                </div>
              </div>
            </div>

            {submissionStatus && (
              <div className="mt-5">
                <LifecycleStepper status={submissionStatus} />
              </div>
            )}
          </div>
        </Card>

        {/* DUE DATE ALERT — hidden once approved, since a completed
    submission has nothing left to be due */}
{dueDateState !== "normal" && submissionStatus !== "APPROVED" && (
  <Alert
    className={
      dueDateState === "overdue"
        ? "border-red-200 bg-red-50 py-2.5"
        : "border-amber-200 bg-amber-50 py-2.5"
    }
  >
    <Clock3
      className={`h-4 w-4 ${
        dueDateState === "overdue" ? "text-red-600" : "text-amber-600"
      }`}
    />
    <AlertTitle
      className={
        dueDateState === "overdue" ? "text-red-900" : "text-amber-900"
      }
    >
      {dueDateState === "overdue" ? "Request overdue" : "Request due soon"}
    </AlertTitle>
    <AlertDescription
      className={
        dueDateState === "overdue" ? "text-red-700" : "text-amber-700"
      }
    >
      Due date:{" "}
      <strong>
        {request.due_date ? formatDate(request.due_date) : "Not specified"}
      </strong>
    </AlertDescription>
  </Alert>
)}
        {/* REQUEST DETAILS — compact card */}
        <Card className="border border-gray-100 shadow-sm">
          <CardHeader className="px-5 pb-2 pt-4">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-[#22243A]">
              <ClipboardList className="h-4 w-4 text-[#1F766D]" />
              Request Details
            </CardTitle>
          </CardHeader>

          <CardContent className="px-5 pb-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <DetailItem icon={MapPin} label="Organization / Site" value={request.org_node_name} />
              <DetailItem icon={CalendarDays} label="Reporting Period" value={request.reporting_period_name} />
              <DetailItem icon={User} label="Assigned To" value={request.assignee_username} />
              <DetailItem
                icon={Clock3}
                label="Due Date"
                value={request.due_date ? formatDate(request.due_date) : "No due date"}
              />
            </div>
          </CardContent>
        </Card>

        {/* INSTRUCTIONS */}
        {request.instructions && (
          <Card className="border border-gray-100 shadow-sm">
            <CardHeader className="px-5 pb-2 pt-4">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-[#22243A]">
                <FileText className="h-4 w-4 text-[#1F766D]" />
                Instructions
              </CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              <p className="whitespace-pre-wrap rounded-lg bg-[#E8F4F2]/40 p-3 text-sm leading-6 text-[#4B5563]">
                {request.instructions}
              </p>
            </CardContent>
          </Card>
        )}

        {/* DATA ENTRY */}
        <Card className="border border-gray-100 shadow-sm">
          <CardHeader className="px-5 pb-2 pt-4">
            <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm font-semibold text-[#22243A]">
                  <ClipboardList className="h-4 w-4 text-[#1F766D]" />
                  Data Entry
                </CardTitle>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Complete the datapoint using the catalog-defined field.
                </p>
              </div>
              {!editable && (
                <Badge variant="outline" className="w-fit text-[11px]">
                  Read only
                </Badge>
              )}
            </div>
          </CardHeader>

          <CardContent className="px-5 pb-5">
            {fieldErrors && (
              <Alert variant="destructive" className="mb-4 py-2.5">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Couldn&apos;t save this entry</AlertTitle>
                <AlertDescription>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4">
                    {Object.entries(fieldErrors).map(([field, message]) => (
                      <li key={field}>
                        <span className="font-medium">{formatStatus(field)}:</span>{" "}
                        {message}
                      </li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            <div className="rounded-lg border border-gray-100 bg-white p-4">
              {datapoint ? (
                <DynamicFieldRenderer
                  datapoint={datapoint}
                  value={value}
                  onChange={setValue}
                  disabled={!editable}
                  readOnly={!editable}
                  required={datapoint.is_required}
                  unitsById={unitsById}
                />
              ) : (
                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                  Loading datapoint definition...
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* ==================================================
            EVIDENCE — no Card, plain section + divider
        ================================================== */}
        <Separator />
        <section className="space-y-3 px-1">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Paperclip className="h-4 w-4 text-[#1F766D]" />
              <h2 className="text-sm font-semibold text-[#22243A]">Evidence</h2>
              <span className="text-xs text-muted-foreground">
                Supporting documents attached to this submission
              </span>
            </div>

            {editable && access.canUploadEvidence && (
              <>
                <input
                  ref={evidenceInputRef}
                  id="m5-evidence-upload"
                  type="file"
                  accept={SUPPORTED_EVIDENCE_ACCEPT}
                  className="hidden"
                  onChange={handleEvidenceUpload}
                  disabled={uploadingEvidence}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleEvidenceButtonClick}
                  disabled={uploadingEvidence}
                >
                  <Upload className="mr-1.5 h-3.5 w-3.5" />
                  {uploadingEvidence ? "Uploading..." : "Upload"}
                </Button>
              </>
            )}
          </div>

          {!access.canViewEvidence ? (
            <p className="rounded-lg border border-dashed border-gray-200 p-5 text-center text-sm text-muted-foreground">
              You don&apos;t have permission to view evidence for this request.
            </p>
          ) : evidenceLoading ? (
            <p className="rounded-lg border border-dashed border-gray-200 p-5 text-center text-sm text-muted-foreground">
              Loading evidence...
            </p>
          ) : !request.submission ? (
            <p className="rounded-lg border border-dashed border-amber-200 bg-amber-50 p-5 text-center text-sm text-amber-800">
              Evidence can be accessed only once this request has a submission record.
            </p>
          ) : evidence.length === 0 ? (
            <p className="rounded-lg border border-dashed border-gray-200 p-5 text-center text-sm text-muted-foreground">
              No evidence uploaded yet.
            </p>
          ) : (
            <div className="space-y-2">
              {evidence.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col gap-3 rounded-lg border border-gray-100 p-3 transition-colors hover:border-[#1F766D]/30 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="rounded-md bg-[#E8F4F2] p-2">
                      <FileText className="h-4 w-4 text-[#1F766D]" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {item.original_filename}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatFileSize(item.size)} • {item.content_type}
                      </p>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void handleEvidenceDownload(item)}
                    >
                      <Download className="mr-1.5 h-3.5 w-3.5" />
                      Download
                    </Button>

                    {editable && access.canDeleteEvidence && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setEvidenceToDelete(item)}
                        aria-label={`Delete evidence ${item.original_filename}`}
                        title="Delete evidence"
                        disabled={deletingEvidence}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ==================================================
            SUBMISSION SUMMARY — no Card
        ================================================== */}
        {request.submission && (
          <>
            <Separator />
            <section className="space-y-3 px-1">
              <div className="flex items-center gap-2">
                <ClipboardCheck className="h-4 w-4 text-[#1F766D]" />
                <h2 className="text-sm font-semibold text-[#22243A]">Submission</h2>
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                <SubmissionBadge
                  status={request.submission.status}
                  requestStatus={request.status}
                />
                {request.submission.submitted_at && (
                  <span className="text-xs text-muted-foreground">
                    Submitted {formatDateTime(request.submission.submitted_at)}
                  </span>
                )}
                {request.submission.approved_at && (
                  <span className="text-xs text-muted-foreground">
                    Approved {formatDateTime(request.submission.approved_at)}
                  </span>
                )}
              </div>

              {request.submission.rejection_reason && (
                <Alert className="border-red-200 bg-red-50 py-2.5">
                  <AlertCircle className="h-4 w-4 text-red-600" />
                  <AlertTitle className="text-red-900">Reviewer feedback</AlertTitle>
                  <AlertDescription className="whitespace-pre-wrap text-red-700">
                    {request.submission.rejection_reason}
                  </AlertDescription>
                </Alert>
              )}
            </section>
          </>
        )}

        {/* REVIEWER ACTIONS */}
        {(canApproveAction || canRejectAction || canReopenAction) && (
          <Card className="border border-[#1F766D]/20 bg-[#1F766D]/[0.03] shadow-sm">
            <CardHeader className="px-5 pb-2 pt-4">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-[#22243A]">
                <ClipboardCheck className="h-4 w-4 text-[#1F766D]" />
                Reviewer Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2 px-5 pb-4">
              {canApproveAction && (
                <Button
                  size="sm"
                  className="bg-[#1F766D] hover:bg-[#195e57]"
                  onClick={() => void handleApprove()}
                  disabled={approving || rejecting}
                >
                  <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                  {approving ? "Approving..." : "Approve"}
                </Button>
              )}
              {canRejectAction && (
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => setRejectDialogOpen(true)}
                  disabled={approving || rejecting}
                >
                  <XCircle className="mr-1.5 h-3.5 w-3.5" />
                  Reject
                </Button>
              )}
              {canReopenAction && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setReopenDialogOpen(true)}
                  disabled={reopening}
                >
                  <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                  Reopen for Editing
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {/* ==================================================
            ACTIVITY HISTORY — no Card
        ================================================== */}
        <Separator />
        <section className="space-y-3 px-1 pb-2">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-[#1F766D]" />
            <h2 className="text-sm font-semibold text-[#22243A]">Activity History</h2>
          </div>

          <HistoryTimeline
            history={history}
            loading={historyLoading}
            unavailable={!request.submission}
          />
        </section>

        <ConfirmDialog
          open={evidenceToDelete !== null}
          title="Delete Evidence"
          description={
            evidenceToDelete
              ? `Are you sure you want to delete "${evidenceToDelete.original_filename}"? This action cannot be undone.`
              : ""
          }
          confirmText="Delete Evidence"
          loading={deletingEvidence}
          onConfirm={() => void handleEvidenceDelete()}
          onCancel={() => {
            if (!deletingEvidence) setEvidenceToDelete(null);
          }}
        />

        <ReasonDialog
          open={rejectDialogOpen}
          title="Reject Submission"
          description="This submission will be sent back to the maker. Explain what needs to change."
          confirmText="Reject Submission"
          destructive
          loading={rejecting}
          onConfirm={(reason) => void handleReject(reason)}
          onCancel={() => setRejectDialogOpen(false)}
        />

        <ReasonDialog
          open={reopenDialogOpen}
          title="Reopen Submission"
          description="This will move the submission back to DRAFT so the maker can edit and resubmit."
          confirmText="Reopen Submission"
          loading={reopening}
          onConfirm={(reason) => void handleReopen(reason)}
          onCancel={() => setReopenDialogOpen(false)}
        />
      </div>
    </AppShell>
  );
}

/* ==========================================================
   LIFECYCLE STEPPER
========================================================== */

function LifecycleStepper({ status }: { status: SubmissionStatus }) {
  const isRejected = status === "REJECTED";

  const steps: Array<{ key: SubmissionStatus; label: string }> = isRejected
    ? [
        { key: "DRAFT", label: "Draft" },
        { key: "SUBMITTED", label: "Submitted" },
        { key: "REJECTED", label: "Rejected" },
      ]
    : [
        { key: "DRAFT", label: "Draft" },
        { key: "SUBMITTED", label: "Submitted" },
        { key: "APPROVED", label: "Approved" },
      ];

  const order: SubmissionStatus[] = ["DRAFT", "SUBMITTED", isRejected ? "REJECTED" : "APPROVED"];
  const currentIndex = order.indexOf(status);

  return (
    <div className="flex items-center">
      {steps.map((step, index) => {
        const isComplete = index < currentIndex;
        const isCurrent = index === currentIndex;
        const isFinalRejected = isRejected && step.key === "REJECTED" && isCurrent;

        return (
          <div key={step.key} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full border-2 text-[11px] font-semibold transition-colors ${
                  isFinalRejected
                    ? "border-red-300 bg-red-500 text-white"
                    : isComplete || isCurrent
                      ? "border-emerald-300 bg-emerald-400 text-[#22243A]"
                      : "border-white/30 bg-white/10 text-white/60"
                }`}
              >
                {isFinalRejected ? (
                  <X className="h-3 w-3" />
                ) : isComplete ? (
                  <Check className="h-3 w-3" />
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={`text-[11px] font-medium ${
                  isComplete || isCurrent ? "text-white" : "text-white/50"
                }`}
              >
                {step.label}
              </span>
            </div>

            {index < steps.length - 1 && (
              <div
                className={`mx-2 h-0.5 flex-1 rounded-full transition-colors ${
                  index < currentIndex ? "bg-emerald-300" : "bg-white/20"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ==========================================================
   API RESPONSE HELPERS
========================================================== */

type ApiDataEnvelope<T> = { data: T };

function unwrapApiData<T>(payload: T | ApiDataEnvelope<T>): T {
  if (payload && typeof payload === "object" && "data" in payload) {
    return (payload as ApiDataEnvelope<T>).data;
  }
  return payload as T;
}

/* ==========================================================
   UNIT HELPERS
========================================================== */

function resolveUnitFamilyId(datapoint: DatapointDetail): string | null {
  const family = datapoint.unit_family;
  if (!family) return null;
  return typeof family === "string" ? family : family.id ?? null;
}

function resolveDefaultUnitId(datapoint: DatapointDetail): string | null {
  const unit = datapoint.default_unit;
  if (!unit) return null;
  return typeof unit === "string" ? unit : unit.id ?? null;
}

function hydrateAnswer(
  request: DataRequestDetail,
  datapoint: DatapointDetail,
  setValue: (value: FieldValue | ((current: FieldValue) => FieldValue)) => void,
  setUnit: (value: string | null) => void,
  setPersistedTableRowIds: (ids: Set<string>) => void,
) {
  const answer = request.submission?.answer;
  const dataType = request.datapoint.data_type;

  if (dataType === "TABLE") {
    const savedRows = answer?.table_rows ?? [];
    setPersistedTableRowIds(new Set(savedRows.map((row) => row.id)));
    setValue(
      hydrateTableDraft(savedRows, datapoint.table_rows ?? [], datapoint.table_columns ?? []),
    );
    setUnit(null);
    return;
  }

  setPersistedTableRowIds(new Set());
  setUnit(answer ? (answer.unit ?? null) : resolveDefaultUnitId(datapoint));
  setValue(answerToFieldValue(answer, dataType));
}

/* ==========================================================
   TABLE SAVE
========================================================== */
async function saveTableRows(
  requestId: string,
  draft: TableAnswerDraft,
  persistedRowIds: Set<string>,
): Promise<void> {
  const payloads = tableDraftToRowPayloads(draft);
  const currentRowIds = new Set(
    draft.filter((row) => row.id).map((row) => row.id as string),
  );

  const removedIds = [...persistedRowIds].filter((id) => !currentRowIds.has(id));

  const errors: unknown[] = [];

  for (const rowId of removedIds) {
    try {
      await DataCaptureApi.deleteTableRow(requestId, rowId);
    } catch (rowError) {
      errors.push(rowError);
    }
  }

  for (let index = 0; index < draft.length; index += 1) {
    const row = draft[index];
    const payload = payloads[index];
    try {
      if (row.id && persistedRowIds.has(row.id)) {
        await DataCaptureApi.updateTableRow(requestId, row.id, payload);
      } else {
        await DataCaptureApi.createTableRow(requestId, payload);
      }
    } catch (rowError) {
      errors.push(rowError);
    }
  }

  if (errors.length > 0) {
    throw errors[0];
  }
}
/* ==========================================================
   HISTORY TIMELINE
========================================================== */

function HistoryTimeline({
  history,
  loading,
  unavailable,
}: {
  history: SubmissionHistory | null;
  loading: boolean;
  unavailable?: boolean;
}) {
  const events = useMemo(() => {
    if (!history) return [];

    const requestEvents = history.request_events.map((event) => ({
      id: `request-${event.id}`,
      eventType: event.event_type,
      actor: event.actor_username,
      reason: event.comment || "",
      createdAt: event.created_at,
    }));

    const submissionEvents = history.submission_events.map((event) => ({
      id: `submission-${event.id}`,
      eventType: event.event_type,
      actor: event.actor_username,
      reason: event.reason || "",
      createdAt: event.created_at,
    }));

    return [...requestEvents, ...submissionEvents].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }, [history]);

  if (loading) {
    return (
      <p className="rounded-lg border border-dashed border-gray-200 p-5 text-center text-sm text-muted-foreground">
        Loading history...
      </p>
    );
  }

  if (unavailable) {
    return (
      <p className="rounded-lg border border-dashed border-amber-200 bg-amber-50 p-5 text-center text-sm text-amber-800">
        History will appear once this request has a submission record.
      </p>
    );
  }

  if (events.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-200 p-5 text-center text-sm text-muted-foreground">
        No history yet — workflow events will appear here as the request progresses.
      </p>
    );
  }

  return (
    <div className="space-y-0">
      {events.map((event, index) => (
        <div key={event.id} className="relative flex gap-3 pb-4 last:pb-0">
          {index < events.length - 1 && (
            <div className="absolute left-[9px] top-6 h-full w-px bg-gray-100" />
          )}
          <div className="relative z-10 mt-1 h-[18px] w-[18px] shrink-0 rounded-full border-[3px] border-background bg-[#1F766D]" />

          <div className="min-w-0 flex-1 rounded-lg border border-gray-100 p-3">
            <div className="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm font-semibold text-[#22243A]">
                {formatStatus(event.eventType)}
              </p>
              <span className="text-[11px] text-muted-foreground">
                {formatDateTime(event.createdAt)}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              By <span className="font-medium text-[#4B5563]">{event.actor}</span>
            </p>
            {event.reason && (
              <p className="mt-2 whitespace-pre-wrap rounded-md bg-muted/30 p-2.5 text-xs leading-5 text-[#4B5563]">
                {event.reason}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ==========================================================
   DETAIL ITEM
========================================================== */

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
    <div className="flex min-w-0 gap-2.5">
      <div className="mt-0.5 shrink-0 rounded-md bg-[#E8F4F2] p-2">
        <Icon className="h-3.5 w-3.5 text-[#1F766D]" />
      </div>
      <div className="min-w-0">
        <Label className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </Label>
        <p className="mt-0.5 truncate text-sm font-semibold text-[#22243A]">{value}</p>
      </div>
    </div>
  );
}

/* ==========================================================
   SUBMISSION BADGE
========================================================== */

type SubmissionBadgeVariant =
  | "default" | "secondary" | "destructive" | "outline" | "success" | "info" | "warning";

interface SubmissionBadgeConfig {
  label: string;
  variant: SubmissionBadgeVariant;
}

function SubmissionBadge({
  status,
  requestStatus,
}: {
  status: SubmissionStatus | null;
  requestStatus: string;
}) {
  if (!status) {
    return (
      <Badge variant="outline" className="border-white/25 bg-white/10 text-[11px] text-white">
        {requestStatus === "OPEN" ? "Not Started" : formatStatus(requestStatus)}
      </Badge>
    );
  }

  const variants: Record<SubmissionStatus, SubmissionBadgeConfig> = {
    DRAFT: { label: "Draft", variant: "warning" },
    SUBMITTED: { label: "Submitted", variant: "info" },
    APPROVED: { label: "Approved", variant: "success" },
    REJECTED: { label: "Rejected", variant: "destructive" },
  };

  const current = variants[status];
  if (!current) {
    return (
      <Badge variant="outline" className="border-white/25 bg-white/10 text-[11px] text-white">
        {formatStatus(status)}
      </Badge>
    );
  }

  return (
    <Badge variant={current.variant} className="text-[11px]">
      {current.label}
    </Badge>
  );
}

/* ==========================================================
   DUE DATE
========================================================== */

function parseDateValue(value: string): Date {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (m) {
    const [, y, mo, d] = m;
    return new Date(Number(y), Number(mo) - 1, Number(d));
  }
  return new Date(value);
}

function getDueDateState(value: string | null): "normal" | "soon" | "overdue" {
  if (!value) return "normal";
  const now = new Date();
  const due = parseDateValue(value);
  now.setHours(0, 0, 0, 0);
  due.setHours(0, 0, 0, 0);
  if (due < now) return "overdue";
  const days = (due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return days <= 3 ? "soon" : "normal";
}

/* ==========================================================
   HELPERS
========================================================== */

function formatDataType(value: string) {
  return value.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatStatus(value: string) {
  return value.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(value: string) {
  const date = parseDateValue(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(date);
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}