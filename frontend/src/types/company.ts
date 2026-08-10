export interface Company {
  id: string;

  /* ==========================================
      Basic Information
  ========================================== */

  company_logo?: string | null;

  company_name: string;
  company_code: string;

  about_company?: string | null;

  date_of_incorporation?: string | null;

  /* ==========================================
      Legal Information
  ========================================== */

  cin_number?: string | null;
  gst_number?: string | null;

  listed_company: boolean;

  stock_exchanges?: string | null;

  paid_up_capital?: string | null;

  turnover?: string | null;

  ownership_form?: string | null;

  /* ==========================================
      Address
  ========================================== */

  registered_address?: string | null;

  corporate_address?: string | null;

  country: string | null;
  state: string | null;
  city: string | null;

  country_name?: string;
  state_name?: string;
  city_name?: string;

  /* ==========================================
      Contact
  ========================================== */

  contact_person: string;

  email: string;

  mobile_number: string;

  website?: string | null;

  /* ==========================================
      Reporting
  ========================================== */

  employee_count: number;

  financial_year_start_month: number;

  /* ==========================================
      Common
  ========================================== */

  is_active: boolean;

  created_at: string;

  updated_at: string;
}

export interface Country {
  id: string;
  name: string;
}

export interface State {
  id: string;
  country: string;
  name: string;
}

export interface City {
  id: string;
  state: string;
  name: string;
}

export interface CompanyPayload {
  /* ==========================================
      Basic Information
  ========================================== */

  company_logo?: File | null;

  company_name: string;

  company_code: string;

  about_company: string;

  date_of_incorporation: string;

  /* ==========================================
      Legal Information
  ========================================== */

  cin_number: string;

  gst_number: string;

  listed_company: boolean;

  stock_exchanges: string;

  paid_up_capital: string;

  turnover: string;

  ownership_form: string;

  /* ==========================================
      Address
  ========================================== */

  registered_address: string;

  corporate_address: string;

  country: string;

  state: string;

  city: string;

  /* ==========================================
      Contact
  ========================================== */

  contact_person: string;

  email: string;

  mobile_number: string;

  website: string;

  /* ==========================================
      Reporting
  ========================================== */

  employee_count: number;

  financial_year_start_month: number;

  /* ==========================================
      Common
  ========================================== */

  is_active: boolean;
}