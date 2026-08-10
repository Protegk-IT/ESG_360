export type PeriodType =
  | "ANNUAL"
  | "HALF_YEARLY"
  | "QUARTERLY"
  | "MONTHLY";

export type ReportingPeriodStatus =
  | "OPEN"
  | "LOCKED"
  | "CLOSED";

export interface ReportingPeriod {
  id: string;

  parent: string | null;

  name: string;

  period_type: PeriodType;

  start_date: string;
  end_date: string;

  status: ReportingPeriodStatus;

  is_baseline_year: boolean;

  locked_at: string | null;

  locked_by: number | null;

  is_active: boolean;

  created_at: string;
  updated_at: string;

  is_editable: boolean;
}

export interface ReportingPeriodFormData {
  parent: string | null;

  name: string;

  period_type: PeriodType;

  start_date: string;

  end_date: string;

  status: ReportingPeriodStatus;

  is_baseline_year: boolean;

  is_active: boolean;
}

export interface GenerateSubPeriodsPayload {
  period_type:
    | "HALF_YEARLY"
    | "QUARTERLY"
    | "MONTHLY";
}