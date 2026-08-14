import api from "@/services/api";

import type {
  Survey,
  SurveyFormData,
  SurveyQuestion,
  SendSurveyResponse,
} from "@/types/materiality/survey";

import type {
  Stakeholder,
} from "@/types/materiality/stakeholder";


const BASE_URL =
  "/materiality/assessments";


const SurveyApi = {
  getSurvey(
    assessmentId: string
  ) {
    return api.get<Survey>(
      `${BASE_URL}/${assessmentId}/survey/`
    );
  },

  updateSurvey(
    assessmentId: string,
    data: Partial<SurveyFormData>
  ) {
    return api.patch<Survey>(
      `${BASE_URL}/${assessmentId}/survey/`,
      data
    );
  },

  generateSurvey(
    assessmentId: string
  ) {
    return api.post(
      `${BASE_URL}/${assessmentId}/survey/generate/`
    );
  },

  getQuestions(
    assessmentId: string
  ) {
    return api.get<SurveyQuestion[]>(
      `${BASE_URL}/${assessmentId}/survey/questions/`
    );
  },

  getStakeholders(
    assessmentId: string
  ) {
    return api.get<Stakeholder[]>(
      `${BASE_URL}/${assessmentId}/stakeholders/`
    );
  },

  sendSurvey(
    assessmentId: string,
    stakeholderIds: string[]
  ) {
    return api.post<SendSurveyResponse>(
      `${BASE_URL}/${assessmentId}/survey/send/`,
      {
        stakeholder_ids: stakeholderIds,
      }
    );
  },

  getSurveyStatus(
    assessmentId: string
  ) {
    return api.get(
      `${BASE_URL}/${assessmentId}/survey/status/`
    );
  },

updateQuestion(
  assessmentId: string,
  questionId: string,
  data: Partial<SurveyQuestion>
) {
  return api.patch<SurveyQuestion>(
    `${BASE_URL}/${assessmentId}/survey/questions/${questionId}/`,
    data
  );
},
};

export default SurveyApi;