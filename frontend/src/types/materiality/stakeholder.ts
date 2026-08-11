export interface StakeholderGroup {
  id: string;
  assessment: string;
  name: string;
  description: string;
  weight: string;
  is_internal: boolean;
  created_at: string;
}

export interface StakeholderGroupFormData {
  name: string;
  description: string;
  weight: string;
  is_internal: boolean;
}

export interface Stakeholder {
  id: string;
  group: string;
  name: string;
  email: string;
  organisation: string;
  designation: string;
  created_at: string;
}

export interface StakeholderFormData {
  group: string;
  name: string;
  email: string;
  organisation: string;
  designation: string;
}