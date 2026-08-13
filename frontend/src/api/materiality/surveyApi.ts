import api from "@/services/api";

import type {
  Survey,
  SurveyFormData,
  SurveyQuestion,
} from "@/types/materiality/survey";

import type {
  Stakeholder,
} from "@/types/materiality/stakeholder";


const BASE_URL =
  "/materiality/assessments";


/* ==========================================================
   RESPONSE TYPES
========================================================== */

export interface SurveyInvitationResult {
  id: string;

  stakeholder_id: string;

  stakeholder_name: string;

  stakeholder_email: string;

  status: string;

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
   SURVEY API
========================================================== */

const SurveyApi = {

  /* ========================================================
     GET SURVEY
  ======================================================== */

  getSurvey(
    assessmentId: string
  ) {
    return api.get<Survey>(
      `${BASE_URL}/${assessmentId}/survey/`
    );
  },


  /* ========================================================
     UPDATE SURVEY
     PATCH:
     /assessments/{id}/survey/
  ======================================================== */

  updateSurvey(
    assessmentId: string,
    data: Partial<SurveyFormData>
  ) {
    return api.patch<Survey>(
      `${BASE_URL}/${assessmentId}/survey/`,
      data
    );
  },


  /* ========================================================
     GENERATE QUESTIONS
  ======================================================== */

  generateSurvey(
    assessmentId: string
  ) {
    return api.post(
      `${BASE_URL}/${assessmentId}/survey/generate/`
    );
  },


  /* ========================================================
     GET QUESTIONS
  ======================================================== */

  getQuestions(
    assessmentId: string
  ) {
    return api.get<SurveyQuestion[]>(
      `${BASE_URL}/${assessmentId}/survey/questions/`
    );
  },


  /* ========================================================
     UPDATE QUESTIONS
  ======================================================== */

  updateQuestions(
    assessmentId: string,
    data: Partial<SurveyQuestion>
  ) {
    return api.patch(
      `${BASE_URL}/${assessmentId}/survey/questions/`,
      data
    );
  },


  /* ========================================================
     GET STAKEHOLDERS
  ======================================================== */

  getStakeholders(
    assessmentId: string
  ) {
    return api.get<Stakeholder[]>(
      `${BASE_URL}/${assessmentId}/stakeholders/`
    );
  },


  /* ========================================================
     SEND SURVEY INVITATIONS
     
     POST:
     /assessments/{id}/survey/send/

     Body:
     {
       stakeholder_ids: string[]
     }
  ======================================================== */

  sendSurvey(
    assessmentId: string,
    stakeholderIds: string[]
  ) {
    return api.post<SendSurveyResponse>(
      `${BASE_URL}/${assessmentId}/survey/send/`,
      {
        stakeholder_ids:
          stakeholderIds,
      }
    );
  },


  /* ========================================================
     GET SURVEY STATUS
  ======================================================== */

  getSurveyStatus(
    assessmentId: string
  ) {
    return api.get(
      `${BASE_URL}/${assessmentId}/survey/status/`
    );
  },

};


export default SurveyApi;