import api from "@/services/api";

import type {
  MaterialityAssessment,
  MaterialityAssessmentFormData,
  AssessmentTopic,
} from "@/types/materiality/assessment";
import type { ReportingPeriod } from "@/types/reporting-period";

const BASE_URL = "/materiality/assessments";

const AssessmentApi = {

  /* ========================================================
     GET ALL ASSESSMENTS
  ======================================================== */

  getAll() {
    return api.get<MaterialityAssessment[]>(
      `${BASE_URL}/`
    );
  },

  /* ========================================================
     GET ASSESSMENT BY ID
  ======================================================== */

  getById(id: string) {
    return api.get<MaterialityAssessment>(
      `${BASE_URL}/${id}/`
    );
  },


  /* ========================================================
     GET REPORTING PERIODS
  ======================================================== */

  getReportingPeriods: async () => {
    const response = await api.get<ReportingPeriod[]>(
      `${BASE_URL}/reporting-periods/`
    );

    return response.data;
  },

  /* ========================================================
     CREATE ASSESSMENT
  ======================================================== */

  create(data: MaterialityAssessmentFormData) {
    return api.post<MaterialityAssessment>(
      `${BASE_URL}/`,
      data
    );
  },

  /* ========================================================
     UPDATE ASSESSMENT
  ======================================================== */

  update(
    id: string,
    data: Partial<MaterialityAssessmentFormData>
  ) {
    return api.put<MaterialityAssessment>(
      `${BASE_URL}/${id}/`,
      data
    );
  },

  /* ========================================================
     PATCH ASSESSMENT
  ======================================================== */

  patch(
    id: string,
    data: Partial<MaterialityAssessmentFormData>
  ) {
    return api.patch<MaterialityAssessment>(
      `${BASE_URL}/${id}/`,
      data
    );
  },

  /* ========================================================
     DELETE ASSESSMENT
  ======================================================== */

  delete(id: string) {
    return api.delete(
      `${BASE_URL}/${id}/`
    );
  },

  /* ========================================================
     GET SELECTED TOPICS FOR ASSESSMENT

     GET:
     /materiality/assessments/<id>/topics/
  ======================================================== */

  getTopicsByAssessment(assessmentId: string) {
    return api.get<AssessmentTopic[]>(
      `${BASE_URL}/${assessmentId}/topics/`
    );
  },

  /* ========================================================
     BULK SELECT SUBTOPICS

     POST:
     /materiality/assessments/<id>/select-topics/

     Body:
     {
       subtopic_ids: string[]
     }
  ======================================================== */

  selectTopics(
    assessmentId: string,
    subtopicIds: string[]
  ) {
    return api.post(
      `${BASE_URL}/${assessmentId}/select-topics/`,
      {
        subtopic_ids: subtopicIds,
      }
    );
  },
};

export default AssessmentApi;