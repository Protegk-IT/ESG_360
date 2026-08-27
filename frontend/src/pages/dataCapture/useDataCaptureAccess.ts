import { useMemo } from "react";

import { useAuth } from "@/context/AuthContext";
import type {
  AuthRoleAssignment,
  AuthUser,
} from "@/types/auth";
import type { Role } from "@/types/role";
import type { OrgNode } from "@/types/organization";
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
   ID COMPARISON
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
   DATE VALIDITY
   ----------------------------------------------------------
   Mirrors the backend assignment validity rules:

     valid_from IS NULL OR valid_from <= today
     valid_to   IS NULL OR valid_to   >= today
========================================================== */

function isAssignmentCurrentlyValid(
  assignment: AuthRoleAssignment,
): boolean {
  if (!assignment.is_active) {
    return false;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (assignment.valid_from) {
    const validFrom = new Date(
      `${assignment.valid_from}T00:00:00`,
    );

    if (validFrom > today) {
      return false;
    }
  }

  if (assignment.valid_to) {
    const validTo = new Date(
      `${assignment.valid_to}T00:00:00`,
    );

    if (validTo < today) {
      return false;
    }
  }

  return true;
}


/* ==========================================================
   ORG NODE TREE FLATTENING
   ----------------------------------------------------------
   `/org/nodes/` currently returns a hierarchical tree.

   The resolver needs a simple:

     node UUID -> OrgNode

   lookup while preserving the original node objects.
========================================================== */

function flattenOrgNodes(
  nodes: OrgNode[],
): Record<string, OrgNode> {
  const result: Record<string, OrgNode> = {};

  const visit = (node: OrgNode) => {
    result[node.id] = node;

    for (const child of node.children ?? []) {
      visit(child);
    }
  };

  for (const node of nodes) {
    visit(node);
  }

  return result;
}

/* ==========================================================
   ROLE LOOKUP
========================================================== */

function buildRoleMap(
  roles: Role[],
): Record<string, Role> {
  const result: Record<string, Role> = {};

  for (const role of roles) {
    result[role.id] = role;
  }

  return result;
}

/* ==========================================================
   ORG NODE SCOPE
   ----------------------------------------------------------
   Mirrors the backend's hierarchical scope behavior:

     requestNode.path.startsWith(assignmentNode.path)

   A null assignment org_node means company-wide access.
========================================================== */

function isOrgNodeInScope(
  assignment: AuthRoleAssignment,
  requestOrgNodeId: string,
  nodesById: Record<string, OrgNode>,
): boolean {
  /*
   * Backend behavior:
   *
   * org_node IS NULL
   *     -> company-wide assignment
   */
  if (!assignment.org_node) {
    return true;
  }

  const assignmentNode =
    nodesById[assignment.org_node];

  const requestNode =
    nodesById[requestOrgNodeId];

  /*
   * Fail closed if the required reference data is missing.
   */
  if (!assignmentNode || !requestNode) {
    return false;
  }

  return requestNode.path.startsWith(
    assignmentNode.path,
  );
}

/* ==========================================================
   ROLE PERMISSION CHECK
   ----------------------------------------------------------
   Important:
   `Role.permissions` contains permission UUIDs.

   `Role.permission_details` contains the actual permission
   codes such as:

     data.enter
     data.submit
     data.approve
     evidence.view
     evidence.upload

   Therefore we MUST check `permission_details.code`.
========================================================== */

function roleGrantsPermission(
  role: Role,
  permissionCode: string,
): boolean {
  if (!role.is_active) {
    return false;
  }

  return role.permission_details.some(
    (permission) =>
      permission.code === permissionCode,
  );
}

/* ==========================================================
   REQUEST-SCOPED PERMISSION
   ----------------------------------------------------------
   This is the core D20 resolver.

   It checks, in order:

     1. assignment is active/current
     2. assignment role exists and is active
     3. assignment role grants the exact permission
     4. assignment module is compatible
     5. assignment OrgNode covers request OrgNode

   Crucially, ALL of these checks are performed against the
   SAME role assignment.
========================================================== */

function assignmentGrantsPermission(
  assignment: AuthRoleAssignment,
  role: Role | undefined,
  permissionCode: string,
  requestOrgNodeId: string,
  nodesById: Record<string, OrgNode>,
): boolean {
  /*
   * Assignment itself must currently qualify.
   */
  if (!isAssignmentCurrentlyValid(assignment)) {
    return false;
  }

  /*
   * The assignment must point to a role that we have loaded.
   */
  if (!role) {
    return false;
  }

  /*
   * The role must contain the requested permission.
   */
  if (
    !roleGrantsPermission(
      role,
      permissionCode,
    )
  ) {
    return false;
  }

  /*
   * Backend derives the module from the permission code:
   *
   *   data.approve      -> data
   *   evidence.view     -> evidence
   */
  const permissionModule =
    permissionCode.split(".", 1)[0];

  /*
   * Match backend behavior:
   *
   * assignment.module_code IS NULL
   * OR
   * assignment.module_code = permission module
   */
  if (
    assignment.module_code !== null &&
    assignment.module_code !== permissionModule
  ) {
    return false;
  }

  /*
   * Finally check the actual OrgNode scope.
   */
  return isOrgNodeInScope(
    assignment,
    requestOrgNodeId,
    nodesById,
  );
}

/* ==========================================================
   REQUEST-SCOPED PERMISSION HELPER
   ----------------------------------------------------------
   A permission is true only when at least ONE individual
   qualifying role assignment grants that permission for the
   request's OrgNode.

   We NEVER combine:

     permission from assignment A
     +
     scope from assignment B
========================================================== */
function hasScopedPermission(
  user: AuthUser,
  rolesById: Record<string, Role>,
  nodesById: Record<string, OrgNode>,
  requestOrgNodeId: string,
  permissionCode: string,
): boolean {
  return user.role_assignments.some(
    (assignment) => {
      if (!isAssignmentCurrentlyValid(assignment)) {
        return false;
      }

      const role = rolesById[assignment.role];

      /*
       * Preferred path:
       * role definition is available.
       */
      if (role) {
        return assignmentGrantsPermission(
          assignment,
          role,
          permissionCode,
          requestOrgNodeId,
          nodesById,
        );
      }

      /*
       * Fallback for normal M5 users who do not have role.view.
       *
       * Use the user's effective permission list only together
       * with THIS SAME assignment's scope.
       *
       * Never combine permission from one assignment with the
       * scope of another assignment.
       */
      if (
        !user.permissions.includes(
          permissionCode,
        )
      ) {
        return false;
      }

      if (!assignment.org_node) {
        return true;
      }

      const scope =
        user.scope_summary.find(
          (item) =>
            item.role ===
              assignment.role_name &&
            sameId(
              item.org_node.id,
              assignment.org_node,
            ),
        );

      if (!scope?.org_node) {
        return false;
      }

      return sameId(
        scope.org_node.id,
        requestOrgNodeId,
      );
    },
  );
}

/* ==========================================================
   ACCESS HOOK
========================================================== */

export function useDataCaptureAccess(
  request: DataRequestDetail | null,
): DataCaptureAccess {
  const {
    user,
    roles,
    orgNodes,
  } = useAuth();

  return useMemo(() => {
    /* ------------------------------------------------------
       NO REQUEST / NO AUTHENTICATED USER
    ------------------------------------------------------ */

    if (!request || !user) {
      return EMPTY_ACCESS;
    }

    /* ------------------------------------------------------
       SUPERUSER
       ------------------------------------------------------
       Superuser retains the existing unconditional access.
    ------------------------------------------------------ */

    if (user.is_superuser) {
      return SUPERUSER_ACCESS;
    }

    /* ------------------------------------------------------
       BUILD REFERENCE MAPS
    ------------------------------------------------------ */

    const rolesById = buildRoleMap(roles);
    const nodesById = flattenOrgNodes(orgNodes);

    /*
     * Request-specific capability resolution cannot safely
     * proceed without the role/scope reference data.
     *
     * Fail closed rather than falling back to the flat
     * `permissions` union.
     */
   const hasScopedData =
  user.role_assignments.length > 0 &&
  user.scope_summary.length > 0;

    /* ------------------------------------------------------
       REQUEST ASSIGNEE
    ------------------------------------------------------ */

    const isAssignee = sameId(
      request.assignee,
      user.id,
    );

    /* ------------------------------------------------------
       SUBMISSION OWNERSHIP
    ------------------------------------------------------ */

    const isSubmitter = sameId(
      request.submission?.submitted_by,
      user.id,
    );

    /* ------------------------------------------------------
       MAKER / ENTRY ACCESS
       ------------------------------------------------------

       data.enter:
         exact permission
         + exact assignment scope
         + assignee

       data.submit:
         exact permission
         + exact assignment scope
         + assignee
    ------------------------------------------------------ */

    const canEnter =
      hasScopedData &&
      isAssignee &&
      hasScopedPermission(
        user,
        rolesById,
        nodesById,
        request.org_node,
        "data.enter",
      );

    const canSubmitDraft =
      hasScopedData &&
      isAssignee &&
      hasScopedPermission(
        user,
        rolesById,
        nodesById,
        request.org_node,
        "data.submit",
      );

    /* ------------------------------------------------------
       EVIDENCE VIEW ACCESS
    ------------------------------------------------------

       Evidence viewing is permission + request scope.

       It does not require assignee status.
    ------------------------------------------------------ */

    const canViewEvidence =
      hasScopedData &&
      hasScopedPermission(
        user,
        rolesById,
        nodesById,
        request.org_node,
        "evidence.view",
      );

    /* ------------------------------------------------------
       EVIDENCE WRITE ACCESS
    ------------------------------------------------------

       Backend uses evidence.upload for this action.

       Existing M5 behavior additionally requires that the
       current user is the request assignee.
    ------------------------------------------------------ */

    const canUploadEvidence =
      hasScopedData &&
      isAssignee &&
      hasScopedPermission(
        user,
        rolesById,
        nodesById,
        request.org_node,
        "evidence.upload",
      );

    const canDeleteEvidence =
      canUploadEvidence;

    /* ------------------------------------------------------
       REVIEW ACCESS
    ------------------------------------------------------

       Backend contract:

         data.approve -> approve
         data.approve -> reject
         data.approve -> reopen

       All three must come from an assignment that:

         - is active/current
         - has a role granting data.approve
         - has compatible module scope
         - covers request.org_node

       Self-approval protection remains in place.
    ------------------------------------------------------ */

    const hasApproveScope =
      hasScopedData &&
      hasScopedPermission(
        user,
        rolesById,
        nodesById,
        request.org_node,
        "data.approve",
      );

    const canApprove =
      hasApproveScope &&
      !isSubmitter;

    const canReject =
      hasApproveScope &&
      !isSubmitter;

    const canReopen =
      hasApproveScope &&
      !isSubmitter;

    /* ------------------------------------------------------
       MANAGER ACCESS
    ------------------------------------------------------ */

    const canManage =
      hasScopedData &&
      hasScopedPermission(
        user,
        rolesById,
        nodesById,
        request.org_node,
        "data.manage",
      );

    /* ------------------------------------------------------
       READ-ONLY VIEWER
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
  }, [request, user, roles, orgNodes]);
}