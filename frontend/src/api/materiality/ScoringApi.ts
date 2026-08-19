import api from "@/services/api";

import type {
  InternalScore,
  InternalScoreUpdate,
  ScoreRunDetail,
  ScoreRunResultsResponse,
  ScoreOverridePayload,
  ScoreOverrideResponse,
  ScoreRunListItem,
} from "@/types/materiality/scoring";

const BASE_URL = "/materiality/assessments";

const ScoringApi = {
  /* ========================================================
     GET INTERNAL SCORES

     GET:
     /materiality/assessments/<id>/internal-scores/

     Returns a bare array (InternalScoreSerializer(many=True).data).
  ======================================================== */

  getInternalScores(assessmentId: string) {
    return api.get<InternalScore[]>(
      `${BASE_URL}/${assessmentId}/internal-scores/`
    );
  },

  /* ========================================================
     UPDATE INTERNAL SCORES

     PUT:
     /materiality/assessments/<id>/internal-scores/

     Body is a BARE ARRAY (`InternalScoreUpdate = InternalScoreEntry[]`),
     not `{ scores: [...] }` — the view does
     `items = request.data; isinstance(items, list)`.
     Response is also a bare array, one saved InternalScore per item.
  ======================================================== */

  updateInternalScores(
    assessmentId: string,
    data: InternalScoreUpdate
  ) {
    return api.put<InternalScore[]>(
      `${BASE_URL}/${assessmentId}/internal-scores/`,
      data
    );
  },

  /* ========================================================
     RUN SCORING

     POST:
     /materiality/assessments/<id>/score/

     Returns ScoreRunSerializer(score_run).data — a single object
     with a nested `topic_results` array.
  ======================================================== */

  runScoring(assessmentId: string) {
    return api.post<ScoreRunDetail>(
      `${BASE_URL}/${assessmentId}/score/`
    );
  },

  /* ========================================================
     GET RESULTS

     GET:
     /materiality/assessments/<id>/results/

     Always returns a SINGLE OBJECT, never an array:
       - ScoreRunDetail when a run exists
       - { detail, topic_results: [] } when none has run yet
  ======================================================== */

  getResults(assessmentId: string) {
    return api.get<ScoreRunResultsResponse>(
      `${BASE_URL}/${assessmentId}/results/`
    );
  },

  /* ========================================================
     SCORE RUN HISTORY

     GET:
     /materiality/assessments/<id>/score-runs/
  ======================================================== */

  getScoreRuns(assessmentId: string) {
    return api.get<ScoreRunListItem[]>(
      `${BASE_URL}/${assessmentId}/score-runs/`
    );
  },

  /* ========================================================
     MANUAL OVERRIDE

     PATCH:
     /materiality/assessments/<id>/topics/<topic_id>/override/

     Response only contains { classification, override_reason } —
     AssessmentTopicOverrideSerializer.Meta.fields.
  ======================================================== */

  overrideClassification(
    assessmentId: string,
    topicId: string,
    data: ScoreOverridePayload
  ) {
    return api.patch<ScoreOverrideResponse>(
      `${BASE_URL}/${assessmentId}/topics/${topicId}/override/`,
      data
    );
  },
};

export default ScoringApi;