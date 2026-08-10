export interface Department {
  id: string;

  company: string;
  company_name: string;

  parent_department: string | null;
  parent_department_name: string | null;

  name: string;
  code: string;

  description: string;

  is_active: boolean;

  created_at?: string;
  updated_at?: string;
}

export interface DepartmentFormData {
  company: string;

  parent_department: string | null;

  name: string;

  code: string;

  description: string;

  is_active: boolean;
}