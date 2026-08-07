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
  is_superuser: boolean;
  is_staff: boolean;
  roles: string[];
  permissions: string[];
}

// Login Response
export interface LoginResponse {
  success: boolean;
  message: string;
  csrf_token: string;
  user: AuthUser;
}