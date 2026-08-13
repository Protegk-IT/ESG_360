// Login Request
export interface LoginForm {
  username: string;
  password: string;
}

// User Information
export interface AuthUser {
  id: number;
  username: string;
  full_name: string;
  email: string;

  role_name?: string;
  department_name?: string;
  designation?: string | null;
  employee_code?: string | null;
  mobile_number?: string | null;

  profile_image: string | null;

  is_active: boolean;
  is_superuser: boolean;
  is_staff: boolean;

  roles: string[];
  permissions: string[];

  role_assignments: unknown[];
  department_assignments: unknown[];

  date_joined: string;
  last_seen: string | null;
}

// Login Response
export interface LoginResponse {
  csrfToken: string;
  user: AuthUser;
}
