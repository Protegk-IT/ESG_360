export interface UserFormData {
  profile_image: File | null;

  full_name: string;
  email: string;
  username: string;
  mobile_number: string;

  company: string;
  role: string;
  role_name: string;
  org_node: string;
  designation: string;
  department: string;
  employee_code: string;

  assigned_plants: number[];

  is_active: boolean;

  password: string;
  confirm_password: string;
}

export interface UserData {
  assigned_plants: never[];
  department: string | null;
  org_node: string | null;
  role: string | null;
  company?: string;
  id: number;
  username: string;
  email: string;
  role_name: string;
  first_name: string;
  last_name: string;
  full_name: string;
  employee_code: string;
  department_name: string;
  designation: string;
  mobile_number: string;
  is_active: boolean;
  is_superuser: boolean;
}
