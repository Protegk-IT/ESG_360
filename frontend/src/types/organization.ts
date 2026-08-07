export type OrgNodeType =
  | "LEGAL_ENTITY"
  | "BUSINESS_UNIT"
  | "DIVISION"
  | "REGION"
  | "FACILITY";

export type ConsolidationMethod =
  | "FULL"
  | "PROPORTIONAL"
  | "EQUITY";

export interface OrgNode {
  id: string;

  /* ==========================================
      Company
  ========================================== */

  company: string;
  company_name?: string;

  parent: string | null;
  parent_name?: string;

  /* ==========================================
      Basic Information
  ========================================== */

  node_type: OrgNodeType;

  code: string;

  name: string;

  depth: number;

  path: string;

  /* ==========================================
      Facility Information
  ========================================== */

  facility_type?: string | null;

  address?: string | null;

  grid_region?: string | null;

  water_stressed_area: boolean;

  latitude?: string | null;

  longitude?: string | null;

  /* ==========================================
      Location
  ========================================== */

  country: string | null;
  country_name?: string;

  state: string | null;
  state_name?: string;

  city: string | null;
  city_name?: string;

  /* ==========================================
      Consolidation
  ========================================== */

  ownership_percentage: string;

  operational_control: boolean;

  consolidation_method: ConsolidationMethod;

  /* ==========================================
      Lifecycle
  ========================================== */

  commissioned_on?: string | null;

  decommissioned_on?: string | null;

  /* ==========================================
      Common
  ========================================== */

  is_active: boolean;

  created_at: string;

  updated_at: string;

  children?: OrgNode[];
}

export interface OrgNodePayload {
  company: string;

  parent: string | null;

  node_type: OrgNodeType;

  code: string;

  name: string;

  facility_type: string;

  address: string;

  grid_region: string;

  water_stressed_area: boolean;

  latitude: string;

  longitude: string;

  country: string;

  state: string;

  city: string;

  ownership_percentage: string;

  operational_control: boolean;

  consolidation_method: ConsolidationMethod;

   commissioned_on: string | null;
  decommissioned_on: string | null;

  is_active: boolean;
}