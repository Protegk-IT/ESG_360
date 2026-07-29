export interface Organization {
  id: string;
  company: string;
  company_name?: string;
  name: string;
  organization_code: string;
  is_active: boolean;
}

export interface Department {
  id: string;
  organization: string;
  organization_name?: string;
  name: string;
  department_code: string;
  is_active: boolean;
}

export interface Facility {
  id: string;
  organization: string;
  organization_name?: string;
  department: string | null;
  department_name?: string;
  name: string;
  facility_code: string;
  facility_type: string;
  is_active: boolean;
}
