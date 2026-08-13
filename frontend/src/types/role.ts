export interface Permission {
  id: string;
  name: string;
  code: string;
  description: string;
}

export interface Role {
  id: string;
  role_code: string;
  role_name: string;
  description: string;
  is_active: boolean;

  permissions: string[];

  permission_details: Permission[];

  created_at: string;
  updated_at: string;

  is_system: boolean;
}

/* ==========================================
   ROLE CREATE / UPDATE
========================================== */

export interface RoleFormData {
  role_code: string;
  role_name: string;
  description: string;
  permissions: string[];
}
