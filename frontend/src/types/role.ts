export interface Permission {
  id: number;
  name: string;
  code: string;
  description: string;
}

export interface Role {
  id: number;
  role_code: string;
  role_name: string;
  description: string;
  is_active: boolean;

  permissions: number[];

  permission_details: Permission[];

  created_at: string;
  updated_at: string;

  is_system_role: boolean;
}

/* ==========================================
   ROLE CREATE / UPDATE
========================================== */

export interface RoleFormData {
  role_code: string;
  role_name: string;
  description: string;
  permissions: number[];
}