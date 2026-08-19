/* ============================================================
   MATERIALITY SCORING TYPES

   These are shaped to match apps/materiality's actual DRF
   serializers and the ScoringViewSet actions — not guessed.
============================================================ */

/* ============================================================
   IMPACT TYPE
============================================================ */

export type ImpactType =
  | "ACTUAL"
  | "POTENTIAL";


/* ============================================================
   MATERIALITY CLASSIFICATION

   Includes INSUFFICIENT_DATA — services/scoring.py's classify()
   returns this when either the primary or secondary score is
   None (e.g. no survey responses yet for a topic).
============================================================ */

export type MaterialityClassification =
  | "MATERIAL"
  | "MONITOR"
  | "NOT_MATERIAL"
  | "DOUBLE_MATERIAL"
  | "IMPACT_MATERIAL"
  | "FINANCIAL_MATERIAL"
  | "INSUFFICIENT_DATA";


/* ============================================================
   INTERNAL SCORE
   Maps to InternalScoreSerializer output (GET .../internal-scores/)
============================================================ */

export interface InternalScore {
  id: string;

  assessment_topic: string;

  /* Read-only, source="assessment_topic.subtopic.name" */
  assessment_topic_name?: string;

  impact_type: ImpactType;

  scale: number;
  scope: number;
  irremediability: number;

  /*
   * NULL when impact_type === "ACTUAL"
   * Required when impact_type === "POTENTIAL"
   * (enforced by InternalScoreSerializer.validate)
   */
  likelihood: number | null;

  financial_magnitude: number;
  financial_likelihood: number;

  rationale: string;

  scored_by?: string;
  scored_at?: string;
}


/* ============================================================
   INTERNAL SCORE FORM DATA
   Used by React forms before sending to backend
============================================================ */

export interface InternalScoreFormData {
  assessment_topic: string;

  impact_type: ImpactType;

  scale: number | null;
  scope: number | null;
  irremediability: number | null;

  likelihood: number | null;

  financial_magnitude: number | null;
  financial_likelihood: number | null;

  rationale: string;
}


/* ============================================================
   INTERNAL SCORE ENTRY
   A single topic's score, as sent inside the PUT array body
============================================================ */

export interface InternalScoreEntry {
  assessment_topic: string;

  impact_type: ImpactType;

  scale: number;
  scope: number;
  irremediability: number;

  likelihood: number | null;

  financial_magnitude: number;
  financial_likelihood: number;

  rationale?: string;
}


/* ============================================================
   INTERNAL SCORE UPDATE PAYLOAD

   PUT:
   /materiality/assessments/{id}/internal-scores/

   IMPORTANT: the view does `items = request.data` and requires
   `isinstance(items, list)` — the body is a BARE ARRAY, one item
   per sub-topic. It is NOT wrapped in an object like
   `{ scores: [...] }`. Sending an object here fails the view's
   own `isinstance` check with "Expected a non-empty list of
   scores."
============================================================ */

export type InternalScoreUpdate = InternalScoreEntry[];


/* ============================================================
   SCORE RUN
   Maps to Django ScoreRun model / base ScoreRunSerializer fields
============================================================ */

export interface ScoreRun {
  id: string;

  assessment: string;

  mode: string;

  thresholds_snapshot: ThresholdsSnapshot;

  group_weights_snapshot: Record<string, unknown>;

  response_count: number;

  invited_count: number;

  method_version: string;

  run_by: string;

  run_at: string;
}


/* ============================================================
   SCORE RUN TOPIC RESULT
   Maps to ScoreRunTopicSerializer output — this is one entry
   inside ScoreRun.topic_results, NOT a standalone endpoint shape.

   Note: primary_score / secondary_score are NEVER null here.
   run_scoring() explicitly defaults them to Decimal("0.00") when
   there's insufficient data — the signal for "no usable data" is
   classification === "INSUFFICIENT_DATA", not a null score.
============================================================ */

export interface GroupBreakdownEntry {
  group_id: string;
  group_name: string;
  weight: string;
  response_count: number;
  average: string | null;
}

export interface ScoreRunTopicResult {
  id: string;

  assessment_topic: string;

  subtopic_code: string;

  subtopic_name: string;

  category_code: string;

  primary_score: number;

  secondary_score: number;

  classification: MaterialityClassification;

  is_override: boolean;

  override_reason: string | null;

  group_breakdown: Record<string, GroupBreakdownEntry[]>
}


/* ============================================================
   SCORE RUN DETAIL
   Full ScoreRunSerializer output — returned by both:
     POST /assessments/{id}/score/            (201)
     GET  /assessments/{id}/results/           (200, when a run exists)
============================================================ */

export interface ScoreRunDetail extends ScoreRun {
  topic_results: ScoreRunTopicResult[];
}


/* ============================================================
   SCORE RUN LIST ITEM
   Lighter shape from ScoreRunListSerializer — no nested topics.

   GET /assessments/{id}/score-runs/
============================================================ */

export interface ScoreRunListItem {
  id: string;
  mode: string;
  response_count: number;
  invited_count: number;
  method_version: string;
  run_by: string;
  run_at: string;
}


/* ============================================================
   RESULTS ENDPOINT RESPONSE

   GET /assessments/{id}/results/

   Always a SINGLE OBJECT, never an array:
     - ScoreRunDetail, when a score run exists
     - { detail: "...", topic_results: [] } when none has run yet
============================================================ */

export type ScoreRunResultsResponse =
  | ScoreRunDetail
  | { detail: string; topic_results: [] };


/* ============================================================
   MATERIALITY RESULT (UI-facing row shape)

   This is what the dashboard's results table actually renders.
   It is NOT sent by the backend directly — loadDashboard() maps
   each ScoreRunTopicResult from ScoreRunResultsResponse.topic_results
   into this shape.
============================================================ */

export interface MaterialityResult {
  id: string;

  assessment_topic: string;

  subtopic_name?: string;
  subtopic_code?: string;
  category_code?: string;

  primary_score: number | null;
  secondary_score: number | null;

  classification: MaterialityClassification;

  is_override?: boolean;

  override_reason?: string | null;

  group_breakdown?: Record<string, GroupBreakdownEntry[]>;
}


/* ============================================================
   OVERRIDE PAYLOAD (request body)

   PATCH:
   /assessments/{id}/topics/{topic_id}/override/
============================================================ */

export interface ScoreOverridePayload {
  classification: MaterialityClassification;

  override_reason: string;
}


/* ============================================================
   OVERRIDE RESPONSE

   AssessmentTopicOverrideSerializer.Meta.fields only includes
   these two fields — the response does NOT echo back id,
   assessment_topic, or is_override.
============================================================ */

export interface ScoreOverrideResponse {
  classification: MaterialityClassification;
  override_reason: string;
}


export interface ThresholdsSnapshot {
  primary_threshold: string | number;
  secondary_threshold: string | number;
  internal_blend_weight: string | number;
}