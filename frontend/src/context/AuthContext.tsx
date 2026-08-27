import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { AuthUser } from "@/types/auth";
import type { Role } from "@/types/role";
import type { OrgNode } from "@/types/organization";

import api, {
  registerLogoutHandler,
  setCsrfToken,
} from "@/services/api";

/* ==========================================================
   AUTH CONTEXT
========================================================== */

interface AuthContextType {
  user: AuthUser | null;
  permissions: string[];

  /*
   * RBAC reference data.
   *
   * These are supplementary to authentication and are never
   * allowed to invalidate an otherwise valid session.
   */
  roles: Role[];
  orgNodes: OrgNode[];

  isAuthenticated: boolean;
  isLoading: boolean;

  login: (user: AuthUser) => void;
  logout: () => void;
}

const AuthContext =
  createContext<AuthContextType | undefined>(
    undefined,
  );

/* ==========================================================
   PROPS
========================================================== */

interface Props {
  children: ReactNode;
}

/* ==========================================================
   AUTH PROVIDER
========================================================== */

export function AuthProvider({
  children,
}: Props) {
  const [user, setUser] =
    useState<AuthUser | null>(null);

  const [permissions, setPermissions] =
    useState<string[]>([]);

  /*
   * Role definitions contain role-level permission details.
   */
  const [roles, setRoles] =
    useState<Role[]>([]);

  /*
   * OrgNode hierarchy used by request-specific scope
   * resolution when the authenticated user is allowed to
   * access the organization-node endpoint.
   */
  const [orgNodes, setOrgNodes] =
    useState<OrgNode[]>([]);

  const [isLoading, setIsLoading] =
    useState(
      () =>
        !["/", "/login"].includes(
          window.location.pathname,
        ),
    );

  const authGeneration = useRef(0);

  /* ========================================================
     LOAD OPTIONAL RBAC REFERENCE DATA
     --------------------------------------------------------
     IMPORTANT:
     - This is NOT authentication.
     - Failure does NOT log the user out.
     - Forbidden reference endpoints are simply treated as
       unavailable.
     - Existing session remains valid.
  ======================================================== */

  const loadRbacReferenceData =
    useCallback(
      async (authUser: AuthUser) => {
        const currentGeneration =
          authGeneration.current;

        /*
         * Clear previous user's RBAC data before loading
         * the new user's reference data.
         */
        setRoles([]);
        setOrgNodes([]);

        /*
         * Only request roles when the current user can read
         * them. This prevents unnecessary 403 responses for
         * users such as ordinary makers.
         */
        const canReadRoles =
          authUser.is_superuser ||
          authUser.permissions.includes(
            "role.view",
          );

        /*
         * Only request OrgNodes when the current user has
         * organization read access.
         *
         * This is supplementary reference data only.
         */
        const canReadOrgNodes =
          authUser.is_superuser ||
          authUser.permissions.includes(
            "organization.view",
          );

        const roleRequest =
          canReadRoles
            ? api
                .get<Role[]>(
                  "/accounts/roles/",
                )
                .catch(() => null)
            : Promise.resolve(null);

        const orgNodeRequest =
          canReadOrgNodes
            ? api
                .get<OrgNode[]>(
                  "/org/nodes/",
                )
                .catch(() => null)
            : Promise.resolve(null);

        const [
          rolesResponse,
          orgNodesResponse,
        ] = await Promise.all([
          roleRequest,
          orgNodeRequest,
        ]);

        /*
         * Ignore late responses belonging to a previous
         * login/logout generation.
         */
        if (
          authGeneration.current !==
          currentGeneration
        ) {
          return;
        }

        if (rolesResponse) {
          setRoles(
            rolesResponse.data ?? [],
          );
        }

        if (orgNodesResponse) {
          setOrgNodes(
            orgNodesResponse.data ?? [],
          );
        }
      },
      [],
    );

  /* ========================================================
     LOGIN
     --------------------------------------------------------
     Existing behavior is preserved:
     - increment auth generation
     - set user immediately
     - set flat permissions
     - remove legacy localStorage cache
  ======================================================== */

  const login = useCallback(
    (authUser: AuthUser) => {
      authGeneration.current += 1;

      setUser(authUser);

      setPermissions(
        authUser.permissions ?? [],
      );

      /*
       * Clear any previous user's supplementary RBAC data
       * before loading the new user's data.
       */
      setRoles([]);
      setOrgNodes([]);

      /*
       * Authentication and authorisation remain server-session
       * state. Preserve the existing localStorage cleanup.
       */
      localStorage.removeItem("user");
      localStorage.removeItem(
        "permissions",
      );

      /*
       * Load optional RBAC reference data in the background.
       *
       * A 403/404/network error here does NOT invalidate login.
       */
      void loadRbacReferenceData(
        authUser,
      );
    },
    [loadRbacReferenceData],
  );

  /* ========================================================
     LOGOUT
  ======================================================== */

  const logout = useCallback(() => {
    authGeneration.current += 1;

    setUser(null);
    setPermissions([]);

    /*
     * Clear supplementary RBAC data as well so no previous
     * user's scope/role information survives the session.
     */
    setRoles([]);
    setOrgNodes([]);

    localStorage.removeItem("user");
    localStorage.removeItem(
      "permissions",
    );
  }, []);

  /* ========================================================
     REGISTER GLOBAL LOGOUT HANDLER
  ======================================================== */

  useEffect(() => {
    registerLogoutHandler(logout);
  }, [logout]);

  /* ========================================================
     RESTORE SESSION
     --------------------------------------------------------
     Authentication bootstrap remains ONLY:
       /accounts/me/
       /accounts/csrf/

     Optional RBAC reference data is loaded afterwards.
  ======================================================== */

  useEffect(() => {
    let mounted = true;

    if (
      ["/", "/login"].includes(
        window.location.pathname,
      )
    ) {
      return () => {
        mounted = false;
      };
    }

    async function restoreSession() {
      const generation =
        authGeneration.current;

      try {
        /*
         * Preserve the original authentication bootstrap.
         *
         * A roles/org-node 403 can no longer cause logout.
         */
        const [
          meResponse,
          csrfResponse,
        ] = await Promise.all([
          api.get<AuthUser>(
            "/accounts/me/",
          ),

          api.get<{ csrfToken: string }>(
            "/accounts/csrf/",
          ),
        ]);

        if (
          !mounted ||
          authGeneration.current !==
            generation
        ) {
          return;
        }

        setCsrfToken(
          csrfResponse.data.csrfToken,
        );

        setUser(
          meResponse.data,
        );

        setPermissions(
          meResponse.data.permissions ??
            [],
        );

        /*
         * Authentication is already restored at this point.
         *
         * Reference data is supplementary and cannot make
         * the authenticated session fail.
         */
        void loadRbacReferenceData(
          meResponse.data,
        );
      } catch {
        /*
         * Preserve the existing behavior:
         * only failure of the actual authentication
         * bootstrap logs the user out.
         */
        if (
          mounted &&
          authGeneration.current ===
            generation
        ) {
          logout();
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      mounted = false;
    };
  }, [
    loadRbacReferenceData,
    logout,
  ]);

  /* ========================================================
     PROVIDER
  ======================================================== */

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,

        roles,
        orgNodes,

        isAuthenticated: !!user,
        isLoading,

        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* ==========================================================
   AUTH HOOK
========================================================== */

export function useAuth() {
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider",
    );
  }

  return context;
}