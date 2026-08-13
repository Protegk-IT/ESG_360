import api from "@/services/api";

import type {
  PublicSurveyData,
} from "@/types/materiality/survey";


const BASE_URL = "/survey";


const PublicSurveyApi = {

  /*
   * IMPORTANT:
   * The exact backend URL has not yet been provided.
   * Replace this path with your actual public-survey endpoint.
   */
  getSurvey(token: string) {
    return api.get<PublicSurveyData>(
      `${BASE_URL}/${token}/`
    );
  },


  /*
   * Auto-save one answer.
   *
   * Replace the URL/method with your actual
   * public response endpoint.
   */
  saveResponse(
    token: string,
    data: {
      question: string;
      value: number;
      comment?: string;
    }
  ) {
    return api.post(
      `${BASE_URL}/${token}/responses/`,
      data
    );
  },


  /*
   * Submit the complete survey.
   *
   * Replace with the actual backend endpoint.
   */
  submitSurvey(token: string) {
    return api.post(
      `${BASE_URL}/${token}/submit/`
    );
  },

};


export default PublicSurveyApi;