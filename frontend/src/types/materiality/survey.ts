export type SurveyStatus =
  | "DRAFT"
  | "READY"
  | "OPEN"
  | "CLOSED";

export type SurveyDimension =
  | "IMPACT"
  | "STAKEHOLDER_IMPORTANCE"
  | "FINANCIAL";

export interface Survey {
  id: string;
  assessment: string;
  title: string;
  intro_text: string;
  closing_text: string;
  opens_at: string | null;
  closes_at: string | null;
  status: SurveyStatus;
  created_at: string;
}

export interface SurveyFormData {
  title: string;
  intro_text: string;
  closing_text: string;
  opens_at: string | null;
  closes_at: string | null;
}

export interface ScaleDefinition {
  id: string;
  assessment: string | null;
  dimension: SurveyDimension;
  name: string;
  created_at: string;
  options?: ScaleOption[];
}

export interface ScaleOption {
  id: string;
  scale: string;
  value: number;
  label: string;
  description: string;
  created_at: string;
}

export interface ScaleDefinitionFormData {
  dimension: SurveyDimension;
  name: string;
}

export interface ScaleOptionFormData {
  value: number;
  label: string;
  description: string;
}
export interface SurveyQuestion {
  id: string;
  survey: string;
  assessment_topic: string;
  assessment_topic_name: string;
  scale: string;
  scale_name: string;
  dimension: SurveyDimension;
  question_text: string;
  help_text: string;
  display_order: number;
  is_required: boolean;
  created_at: string;
}
export interface SurveyQuestionFormData {
  assessment_topic: string;
  scale: string;
  dimension: SurveyDimension;
  question_text: string;
  help_text: string;
  display_order: number;
  is_required: boolean;
}

export interface SurveyInvitationResult {
  id: string;
  stakeholder_id: string;
  stakeholder_name: string;
  stakeholder_email: string;
  status:
    | "NOT_SENT"
    | "SENT"
    | "OPENED"
    | "SUBMITTED";
  sent_at: string | null;
  token: string;
  survey_url: string;
}

export interface SendSurveyResponse {
  success: boolean;
  message: string;
  survey_id: string;
  count: number;
  invitations: SurveyInvitationResult[];
}

export type SurveyInvitationStatus =
  | "NOT_SENT"
  | "SENT"
  | "OPENED"
  | "SUBMITTED";


export interface PublicSurveyOption {
  id: string;
  value: number;
  label: string;
  description: string;
}


export interface PublicSurveyQuestion
  extends SurveyQuestion {
  scale_options: PublicSurveyOption[];
  category_id: string;
  category_name: string;
  subtopic_id: string;
  subtopic_name: string;
}


export interface PublicSurveyResponse {
  question: string;
  value: number | null;
  comment: string;
  answered_at: string | null;
}


export interface PublicSurveyData {
  survey: Survey;
  invitation: {
    token: string;
    status: SurveyInvitationStatus;
  };
  questions: PublicSurveyQuestion[];
  responses: PublicSurveyResponse[];
}