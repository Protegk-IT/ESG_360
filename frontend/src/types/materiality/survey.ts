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


/* ==========================================================
   SURVEY INVITATION
========================================================== */

export type SurveyInvitationStatus =
  | "NOT_SENT"
  | "SENT"
  | "OPENED"
  | "SUBMITTED";


export interface SurveyInvitationResult {
  id: string;
  stakeholder_id: string;
  stakeholder_name: string;
  stakeholder_email: string;
  status: SurveyInvitationStatus;
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


/* ==========================================================
   PUBLIC SURVEY
========================================================== */

export interface PublicSurveyOption {
  id: string;
  value: number;
  label: string;
  description: string;
}


/*
 * This matches:
 *
 * "scale": {
 *   "id": ...,
 *   "dimension": ...,
 *   "name": ...,
 *   "options": [...]
 * }
 */
export interface PublicSurveyScale {
  id: string;
  dimension: SurveyDimension;
  name: string;
  options: PublicSurveyOption[];
}


/*
 * This matches:
 *
 * "response": {
 *   "id": ...,
 *   "question": ...,
 *   "value": ...,
 *   "comment": ...,
 *   "answered_at": ...
 * }
 *
 * or null when unanswered.
 */
export interface PublicSurveySavedResponse {
  id: string;
  question: string;
  value: number;
  comment: string;
  answered_at: string | null;
}


/*
 * Exact question shape returned by
 * build_public_survey_response()
 */
export interface PublicSurveyQuestion {
  id: string;

  assessment_topic: string;

  category_name: string;

  topic_name: string;

  subtopic_name: string;

  dimension: SurveyDimension;

  question_text: string;

  help_text: string;

  display_order: number;

  is_required: boolean;

  scale: PublicSurveyScale;

  response: PublicSurveySavedResponse | null;
}


/*
 * Invitation information returned by
 * the public survey GET endpoint.
 */
export interface PublicSurveyInvitation {
  id: string;

  status: SurveyInvitationStatus;

  first_opened_at: string | null;

  submitted_at: string | null;

  is_submitted: boolean;
}


/*
 * Survey information returned by the
 * public survey GET endpoint.
 *
 * Your backend does not return `assessment`
 * or `created_at` here, so they are not included.
 */
export interface PublicSurveyInfo {
  id: string;

  title: string;

  intro_text: string;

  closing_text: string;

  status: SurveyStatus;

  opens_at: string | null;

  closes_at: string | null;
}


/*
 * Normal public survey response.
 */
export interface PublicSurveyData {
  success: boolean;

  survey: PublicSurveyInfo;

  invitation: PublicSurveyInvitation;

  questions: PublicSurveyQuestion[];
}


/*
 * Returned when the stakeholder has
 * already submitted the survey.
 */
export interface PublicSurveyAlreadySubmitted {
  success: true;

  submitted: true;

  message: string;

  submitted_at: string | null;
}


export type PublicSurveyGetResponse =
  | PublicSurveyData
  | PublicSurveyAlreadySubmitted;