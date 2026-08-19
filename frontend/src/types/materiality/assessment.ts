import type { ReportingPeriod } from "../reporting-period";

export type AssessmentMode =
  | "SINGLE"
  | "DOUBLE";

export type AssessmentStatus =
  | "DRAFT"
  | "IN_PROGRESS"
  | "SCORED"
  | "COMPLETED"
  | "APPROVED";


export interface MaterialityAssessment {
  is_assessment_completed: unknown;
  reporting_period_name: string;
  id: string;

  company: string;

  name: string;

  financial_year: string;

  period_start: string;

  period_end: string;

  reporting_period: string;

  reporting_period_details?: ReportingPeriod;

  mode: AssessmentMode;

  status: AssessmentStatus;

  primary_threshold: number;

  secondary_threshold: number;

  scale_min: number;

  scale_max: number;

  internal_blend_weight: string;

  is_locked: boolean;

  created_by: number;

  approved_by: number | null;

  approved_at: string | null;

  created_at: string;

  updated_at?: string;

  progress_percentage?: number | null;
  progress?: number | null;
  current_step?: string | null;
  current_step_url?: string | null;
  completed_steps?: number | null;
  total_steps?: number | null;
}


/* ==========================================================
   CREATE / UPDATE FORM
========================================================== */

export interface MaterialityAssessmentFormData {
  primary_threshold: number;
  secondary_threshold: number;
  name: string;
  reporting_period: string;
  mode: AssessmentMode;
}


/* ==========================================================
   DISPLAY LABELS
========================================================== */

export const ASSESSMENT_MODE_LABELS: Record<
  AssessmentMode,
  string
> = {
  SINGLE:"Single Materiality",
  DOUBLE: "Double Materiality",
};


export const ASSESSMENT_STATUS_LABELS: Record<
  AssessmentStatus,
  string
> = {
  DRAFT: "Draft",
  IN_PROGRESS: "In Progress",
  SCORED: "Scored",
  COMPLETED: "Completed",
  APPROVED: "Approved",
};

/* ==========================================================
   ASSESSMENT TOPIC
========================================================== */
export interface AssessmentTopic {
  id: string;
  assessment: string;
  subtopic: string;
  subtopic_name: string;
  topic_name: string;
  category_name: string;
  is_included: boolean;
  display_order: number;
  primary_score: string | null;
  secondary_score: string | null;
  classification: string;
  is_override: boolean;
  override_reason: string;
  override_by: number | null;
  created_at: string;
  updated_at: string;
}

/* ==========================================================
   ASSESSMENT TOPIC — TREE DISPLAY
========================================================== */

export interface AssessmentTopicTreeItem
  extends AssessmentTopic {
  subtopic_name: string;
  subtopic_code: string;

  topic_id: string;
  topic_name: string;
  topic_code: number;

  category_id: string;
  category_name: string;
  category_code: string;
}


/* ==========================================================
   BULK TOPIC SELECTION
========================================================== */

export interface AssessmentTopicSelection {
  subtopic: string;
  is_included: boolean;
  display_order?: number;
}


/* ==========================================================
   BULK SAVE PAYLOAD
========================================================== */

export interface AssessmentTopicBulkPayload {
  assessment: string;
  topics: AssessmentTopicSelection[];
}
