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
import type { SurveyGroupLink, SurveyInvitationResult } from "@/types/materiality/survey";


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

  getInvitations(assessmentId: string) {
    return api.get<SurveyInvitationResult[]>(
      `${BASE_URL}/${assessmentId}/survey/invitations/`
    );
  },

  getGroupLinks(assessmentId: string) {
    return api.get<SurveyGroupLink[]>(
      `${BASE_URL}/${assessmentId}/survey/group-links/`
    );
  },

  prepareDistribution(assessmentId: string) {
    return api.post(`${BASE_URL}/${assessmentId}/survey/prepare-distribution/`);
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

  openSurvey(assessmentId: string) {
    return api.post<Survey>(`${BASE_URL}/${assessmentId}/survey/open/`);
  },

  closeSurvey(assessmentId: string) {
    return api.post<Survey>(`${BASE_URL}/${assessmentId}/survey/close/`);
  },

updateQuestion(
  assessmentId: string,
  questionId: string,
  data: Partial<SurveyQuestion>
) {
  return api.patch<SurveyQuestion>(
    `${BASE_URL}/${assessmentId}/survey/questions/`,
    { ...data, id: questionId }
  );
},
};

export default SurveyApi;
