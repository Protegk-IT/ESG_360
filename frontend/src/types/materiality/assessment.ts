export type AssessmentMode =
  | "IMPACT"
  | "FINANCIAL"
  | "DOUBLE";

export type AssessmentStatus =
  | "DRAFT"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "APPROVED";


export interface MaterialityAssessment {
  id: string;

  company: string;

  name: string;

  financial_year: string;

  period_start: string;

  period_end: string;

  mode: AssessmentMode;

  status: AssessmentStatus;

  primary_threshold: string;

  secondary_threshold: string;

  scale_min: number;

  scale_max: number;

  internal_blend_weight: string;

  is_locked: boolean;

  created_by: number;

  approved_by: number | null;

  approved_at: string | null;

  created_at: string;

  updated_at?: string;
}


/* ==========================================================
   CREATE / UPDATE FORM
========================================================== */

export interface MaterialityAssessmentFormData {
  name: string;

  financial_year: string;

  period_start: string;

  period_end: string;

  mode: AssessmentMode;
}


/* ==========================================================
   DISPLAY LABELS
========================================================== */

export const ASSESSMENT_MODE_LABELS: Record<
  AssessmentMode,
  string
> = {
  IMPACT: "Impact Materiality",
  FINANCIAL:"Financial Materiality",
  DOUBLE: "Double Materiality",
};


export const ASSESSMENT_STATUS_LABELS: Record<
  AssessmentStatus,
  string
> = {
  DRAFT: "Draft",
  IN_PROGRESS: "In Progress",
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