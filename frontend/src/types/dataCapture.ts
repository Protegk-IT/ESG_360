import type { DatapointDataType } from "@/types/datapoint";

/* ==========================================================
   REQUEST STATUS
========================================================== */

export type DataRequestStatus =
  | "OPEN"
  | "COMPLETED"
  | "CANCELLED";

export type SubmissionStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "APPROVED"
  | "REJECTED";

/* ==========================================================
   PAGINATION
========================================================== */

export interface PaginatedResponse<T> {
  data: PaginatedResponse<EvidenceFile>;
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/* ==========================================================
   DATAPOINT REFERENCE
========================================================== */

export interface DataCaptureDatapointReference {
  id: string;
  code: string;
  label: string;
  data_type: DatapointDataType;
  is_required: boolean;
  allow_dynamic_rows: boolean;
}

/* ==========================================================
   TABLE CELL
========================================================== */

export interface AnswerTableCell {
  id: string;
  column: string;
  column_code: string;
  column_label: string;

  decimal_value: number | string | null;
  integer_value: number | null;
  text_value: string | null;
  boolean_value: boolean | null;
  selected_option: string | null;
  date_value: string | null;

  unit: string | null;
}

/* ==========================================================
   TABLE ROW
========================================================== */

export interface AnswerTableRow {
  id: string;
  definition_row: string | null;
  label: string;
  display_order: number;
  cells: AnswerTableCell[];
}

/* ==========================================================
   ANSWER
========================================================== */

export interface M5Answer {
  id: string;

  decimal_value: number | string | null;
  integer_value: number | null;
  text_value: string | null;
  boolean_value: boolean | null;
  selected_option: string | null;
  date_value: string | null;

  unit: string | null;

  entered_by: string | null;

  table_rows: AnswerTableRow[];

  created_at: string;
  updated_at: string;
}

/* ==========================================================
   SUBMISSION
========================================================== */

export interface Submission {
  id: string;
  status: SubmissionStatus;

  submitted_by: string | null;
  submitted_at: string | null;

  approved_by: string | null;
  approved_at: string | null;

  rejection_reason: string | null;

  rejected_by: string | null;
  rejected_at: string | null;

  reopened_by: string | null;
  reopened_at: string | null;

  answer: M5Answer | null;

  created_at: string;
  updated_at: string;
}

/* ==========================================================
   REQUEST LIST
========================================================== */

export interface DataRequestListItem {
  id: string;

  datapoint: string;
  datapoint_code: string;
  datapoint_label: string;

  org_node: string;
  org_node_name: string;

  reporting_period: string;
  reporting_period_name: string;

  module_code: string;

  assignee: string;
  assignee_username: string;

  due_date: string | null;

  status: DataRequestStatus;
  submission_status: SubmissionStatus | null;

  created_at: string;
  updated_at: string;
}

/* ==========================================================
   REQUEST DETAIL
========================================================== */
export interface DataRequestDetail {
  id: string;

  datapoint: DataCaptureDatapointReference;

  org_node: string;
  org_node_name: string;

  reporting_period: string;
  reporting_period_name: string;

  module_code: string;

  assignee: string;
  assignee_username: string;

  requested_by: string;

  due_date: string | null;

  status: DataRequestStatus;

  instructions: string;

  submission: Submission | null;

  created_at: string;
  updated_at: string;
}
/* ==========================================================
   CREATE REQUEST
========================================================== */

export interface CreateDataRequestPayload {
  datapoint: string;
  org_node: string;
  reporting_period: string;
  assignee: string;

  due_date?: string | null;
  instructions?: string;
}

/* ==========================================================
   REASSIGN REQUEST
========================================================== */

export interface ReassignDataRequestPayload {
  assignee: string;
  reason?: string;
}

/* ==========================================================
   SCALAR ANSWER WRITE
========================================================== */

export interface TypedValueWritePayload {
  decimal_value?: number | string | null;
  integer_value?: number | null;
  text_value?: string | null;
  boolean_value?: boolean | null;
  selected_option?: string | null;
  date_value?: string | null;

  unit?: string | null;
}

/* ==========================================================
   TABLE CELL WRITE
========================================================== */

export interface TableCellWritePayload extends TypedValueWritePayload {
  column: string;
}

/* ==========================================================
   TABLE ROW WRITE
========================================================== */

export interface TableRowWritePayload {
  definition_row?: string | null;
  label?: string;
  display_order?: number;

  cells?: TableCellWritePayload[];
}

/* ==========================================================
   EVIDENCE
========================================================== */

export interface EvidenceFile {
  id: string;

  submission: string;
  answer: string | null;

  original_filename: string;
  content_type: string;
  size: number;

  uploaded_by: string;
  uploaded_by_username: string;

  created_at: string;
  updated_at: string;
}

/* ==========================================================
   HISTORY
========================================================== */

export interface SubmissionHistoryEvent {
  id: string;

  event_type: string;

  from_status: SubmissionStatus | null;
  to_status: SubmissionStatus | null;

  actor: string;
  actor_username: string;

  reason: string;
  details: Record<string, unknown>;

  created_at: string;
}

export interface DataRequestHistoryEvent {
  id: string;

  event_type: string;

  actor: string;
  actor_username: string;

  previous_assignee: string | null;
  assignee: string | null;

  comment: string;

  created_at: string;
}

export interface SubmissionHistory {
  data: SubmissionHistory;
  request_events: DataRequestHistoryEvent[];
  submission_events: SubmissionHistoryEvent[];
}

/* ==========================================================
   LIFECYCLE ACTIONS
========================================================== */

export interface ReasonPayload {
  reason: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}