import api from "@/services/api";

import type {
  InternalScore,
  InternalScorePayload,
  ScoreRun,
  MaterialityResult,
  ScoreOverridePayload,
} from "@/types/materiality/scoring";

const BASE_URL = "/materiality/assessments";

const ScoringApi = {
  /* ========================================================
     GET INTERNAL SCORES

     GET:
     /materiality/assessments/<id>/internal-scores/
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
  ======================================================== */

  updateInternalScores(
    assessmentId: string,
    data: InternalScorePayload
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
  ======================================================== */

  runScoring(assessmentId: string) {
    return api.post<ScoreRun>(
      `${BASE_URL}/${assessmentId}/score/`
    );
  },

  /* ========================================================
     GET RESULTS

     GET:
     /materiality/assessments/<id>/results/
  ======================================================== */

  getResults(assessmentId: string) {
    return api.get<MaterialityResult[]>(
      `${BASE_URL}/${assessmentId}/results/`
    );
  },

  /* ========================================================
     MANUAL OVERRIDE

     PATCH:
     /materiality/assessments/<id>/topics/<topic_id>/override/
  ======================================================== */

  overrideClassification(
    assessmentId: string,
    topicId: string,
    data: ScoreOverridePayload
  ) {
    return api.patch(
      `${BASE_URL}/${assessmentId}/topics/${topicId}/override/`,
      data
    );
  },
};

export default ScoringApi;