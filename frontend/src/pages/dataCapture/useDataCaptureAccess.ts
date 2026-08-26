import { useMemo } from "react";

import { useAuth } from "@/context/AuthContext";
import type { DataRequestDetail } from "@/types/dataCapture";

/* ==========================================================
   DATA CAPTURE ACCESS
========================================================== */

export interface DataCaptureAccess {
  canViewEvidence: boolean;

  isAssignee: boolean;
  isSubmitter: boolean;

  canEnter: boolean;
  canSubmitDraft: boolean;

  canUploadEvidence: boolean;
  canDeleteEvidence: boolean;

  canApprove: boolean;
  canReject: boolean;
  canReopen: boolean;

  canManage: boolean;

  isReadOnlyViewer: boolean;
}

/* ==========================================================
   EMPTY ACCESS
========================================================== */

const EMPTY_ACCESS: DataCaptureAccess = {
  canViewEvidence: false,

  isAssignee: false,
  isSubmitter: false,

  canEnter: false,
  canSubmitDraft: false,

  canUploadEvidence: false,
  canDeleteEvidence: false,

  canApprove: false,
  canReject: false,
  canReopen: false,

  canManage: false,

  isReadOnlyViewer: true,
};

/* ==========================================================
   SUPERUSER ACCESS
   ----------------------------------------------------------
   Superuser is intentionally handled in one place so the
   page does not need scattered `user.is_superuser` checks.
========================================================== */

const SUPERUSER_ACCESS: DataCaptureAccess = {
  canViewEvidence: true,

  isAssignee: true,
  isSubmitter: false,

  canEnter: true,
  canSubmitDraft: true,

  canUploadEvidence: true,
  canDeleteEvidence: true,

  canApprove: true,
  canReject: true,
  canReopen: true,

  canManage: true,

  isReadOnlyViewer: false,
};

/* ==========================================================
   HELPER
   ----------------------------------------------------------
   Backend IDs may arrive as strings while AuthContext may
   expose a numeric user ID. Compare their string forms so
   the permission check is type-safe and consistent.
========================================================== */

function sameId(
  first: string | number | null | undefined,
  second: string | number | null | undefined,
): boolean {
  if (
    first === null ||
    first === undefined ||
    second === null ||
    second === undefined
  ) {
    return false;
  }

  return String(first) === String(second);
}

/* ==========================================================
   ACCESS HOOK
========================================================== */

export function useDataCaptureAccess(
  request: DataRequestDetail | null,
): DataCaptureAccess {
  const { user, permissions } = useAuth();

  return useMemo(() => {
    /* ------------------------------------------------------
       No request / no authenticated user
    ------------------------------------------------------ */

    if (!request || !user) {
      return EMPTY_ACCESS;
    }

    /* ------------------------------------------------------
       SUPERUSER
       ------------------------------------------------------
       Superuser bypasses normal permission/scope checks.
    ------------------------------------------------------ */

    if (user.is_superuser) {
      return SUPERUSER_ACCESS;
    }

    /* ------------------------------------------------------
       PERMISSION HELPER
    ------------------------------------------------------ */

    const hasPermission = (permission: string): boolean =>
      permissions.includes(permission);

    /* ------------------------------------------------------
       REQUEST SCOPE
    ------------------------------------------------------ */

    const isAssignee = sameId(
      request.assignee,
      user.id,
    );

    /* ------------------------------------------------------
       SUBMISSION OWNERSHIP
       ------------------------------------------------------
       The M5 response exposes `submitted_by` as an ID.

       Determine whether the current authenticated user is the
       person who submitted the request.
    ------------------------------------------------------ */

    const isSubmitter = sameId(
      request.submission?.submitted_by,
      user.id,
    );

    /* ------------------------------------------------------
       MAKER / ENTRY ACCESS

       data.enter  -> edit answers
       data.submit -> submit draft

       Both are restricted to the request assignee.
    ------------------------------------------------------ */

    const canEnter =
      hasPermission("data.enter") &&
      isAssignee;

    const canSubmitDraft =
      hasPermission("data.submit") &&
      isAssignee;

    /* ------------------------------------------------------
       EVIDENCE VIEW ACCESS

       evidence.view controls whether evidence metadata/files
       can be viewed through the M5 evidence workflow.

       This is intentionally independent from evidence.upload.
       A reviewer may be allowed to view evidence without being
       allowed to upload/delete it.
    ------------------------------------------------------ */

    const canViewEvidence =
      hasPermission("evidence.view");

    /* ------------------------------------------------------
       EVIDENCE WRITE ACCESS

       The backend contract uses evidence.upload for uploading
       evidence. Delete follows the same request-scoped maker
       capability rather than inventing evidence.delete.
    ------------------------------------------------------ */

    const canUploadEvidence =
      hasPermission("evidence.upload") &&
      isAssignee;

    const canDeleteEvidence =
      canUploadEvidence;

    /* ------------------------------------------------------
       REVIEW ACCESS

       Backend contract:

         approve -> data.approve
         reject  -> data.approve
         reopen  -> data.approve

       Self-approval protection:
       a non-superuser who submitted the request must not get
       approve/reject controls.

       Backend authorization remains authoritative.
    ------------------------------------------------------ */

    const canApprove =
      hasPermission("data.approve") &&
      !isSubmitter;

    const canReject =
      hasPermission("data.approve") &&
      !isSubmitter;

    const canReopen =
      hasPermission("data.approve") &&
  !isSubmitter;

    /* ------------------------------------------------------
       MANAGER ACCESS
    ------------------------------------------------------ */

    const canManage =
      hasPermission("data.manage");

    /* ------------------------------------------------------
       READ-ONLY VIEWER

       A user is considered read-only when they have none of
       the mutation/review/management capabilities exposed by
       this request workspace.

       Evidence view alone does not make the user editable.
    ------------------------------------------------------ */

    const isReadOnlyViewer =
  !canEnter &&
  !canSubmitDraft &&
  !canApprove &&
  !canReject &&
  !canReopen &&
  !canManage;

    /* ------------------------------------------------------
       FINAL ACCESS OBJECT
    ------------------------------------------------------ */

    return {
      canViewEvidence,

      isAssignee,
      isSubmitter,

      canEnter,
      canSubmitDraft,

      canUploadEvidence,
      canDeleteEvidence,

      canApprove,
      canReject,
      canReopen,

      canManage,

      isReadOnlyViewer,
    };
  }, [request, user, permissions]);
}