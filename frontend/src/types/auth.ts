

// ==========================================================
// LOGIN REQUEST
// ==========================================================

export interface LoginForm {
  username: string;
  password: string;
}

// ==========================================================
// ROLE ASSIGNMENT
// ==========================================================

export interface AuthRoleAssignment {
  id: string;

  user: number;
  user_name: string;

  role: string;
  role_name: string;

  org_node: string | null;
  org_node_name: string | null;

  module_code: string | null;
  framework_code: string | null;

  valid_from: string | null;
  valid_to: string | null;

  is_active: boolean;

  created_at: string;
  updated_at: string;
}

// ==========================================================
// DEPARTMENT ASSIGNMENT
// ==========================================================

export interface AuthDepartmentAssignment {
  id: string;

  user: number;
  user_name: string;

  department: string;
  is_primary: boolean;

  created_at: string;
  updated_at: string;
}

// ==========================================================
// USER INFORMATION
// ==========================================================

export interface AuthUser {
  id: number;

  username: string;
  full_name: string;
  email: string;

  first_name?: string;
  last_name?: string;

  role?: string | null;
  role_name?: string;

  department?: string | null;
  department_name?: string;

  designation?: string | null;
  employee_code?: string | null;
  mobile_number?: string | null;

  profile_image: string | null;

  is_active: boolean;
  is_superuser: boolean;
  is_staff: boolean;

  // ========================================================
  // RBAC
  // ========================================================

  /*
   * Existing flat permission union.
   *
   * Preserve this because AuthContext/sidebar already use it.
   */
  roles: string[];

  permissions: string[];

  /*
   * Concrete role + OrgNode assignments.
   */
  role_assignments: AuthRoleAssignment[];

  scope_summary: AuthScopeSummary[];

  /*
   * Existing backend response.
   */
  department_assignments: AuthDepartmentAssignment[];

  /*
   * Optional role definitions loaded by the frontend for
   * request-specific Role + Scope capability resolution.
   *
   * This is NOT part of the current /accounts/me/ response.
   * It is populated separately in AuthContext.
   */

  /*
   * Organization scopes are resolved separately from
   * /org/nodes/ and therefore are not stored on AuthUser.
   */

  date_joined: string;
  last_seen: string | null;
}

// ==========================================================
// LOGIN RESPONSE
// ==========================================================

export interface LoginResponse {
  csrfToken: string;
  user: AuthUser;
}

export interface AuthScopeSummary {
  role: string;

  org_node: {
    id: string;
    company: string;
    company_name?: string;
    parent: string | null;
    parent_name?: string;
    node_type: string;
    code: string;
    name: string;
    depth: number;
    path: string;

    facility_type?: string | null;
    address?: string | null;
    grid_region?: string | null;
    water_stressed_area?: boolean;
    latitude?: string | null;
    longitude?: string | null;

    country?: string | null;
    country_name?: string;
    state?: string | null;
    state_name?: string;
    city?: string | null;
    city_name?: string;

    ownership_percentage?: string;
    operational_control?: boolean;
    consolidation_method?: string;

    commissioned_on?: string | null;
    decommissioned_on?: string | null;

    is_active: boolean;
    created_at: string;
    updated_at: string;
  };

  module_code: string | null;
  framework_code: string | null;

  valid_from: string | null;
  valid_to: string | null;
}