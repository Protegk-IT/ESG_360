export interface Country {
  id: string;
  name: string;
  iso_code: string;
  is_active: boolean;
}

export interface State {
  id: string;
  country: string;
  name: string;
  state_code: string;
  is_active: boolean;
}

export interface City {
  id: string;
  country: string;
  state: string;
  name: string;
  is_active: boolean;
}

export interface Company {
  id: string;
  company_code: string;
  company_name: string;
  contact_person: string;
  email: string;
  mobile_number: string;
  is_active: boolean;
}
