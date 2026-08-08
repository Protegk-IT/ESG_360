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

  role_name: string;
  department_name: string;
  designation: string;
  employee_code: string;
  mobile_number: string;

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
  success: boolean;
  message: string;
  csrf_token: string;
  user: AuthUser;
}