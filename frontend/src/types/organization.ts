export interface OrgNode {
  id: string;
  name: string;
  node_type: "LEGAL_ENTITY" | "BUSINESS_UNIT" | "DIVISION" | "REGION" | "FACILITY";
  node_code: string | null;
  company: string;
  company_name?: string;
  parent: string | null;
  parent_name?: string;
  description: string;
  ownership_percentage: string | null;
  operational_control: boolean;
  financial_control: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  children_count: number;
}
