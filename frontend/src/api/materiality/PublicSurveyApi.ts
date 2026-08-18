import api from "@/services/api";

import type {
  PublicSurveyGetResponse,
} from "@/types/materiality/survey";

const BASE_URL =
  "/public/materiality/survey";

const PublicSurveyApi = {
  getSurvey(token: string, responseToken?: string) {
    return api.get<PublicSurveyGetResponse>(
      `${BASE_URL}/${token}/`,
      { params: responseToken ? { response_token: responseToken } : undefined }
    );
  },

  saveResponse(
    token: string,
    data: {
      question: string;
      value: number;
      comment?: string;
    },
    responseToken?: string,
  ) {
    return api.post(
      `${BASE_URL}/${token}/answer/`,
      { ...data, response_token: responseToken }
    );
  },

  submitSurvey(token: string, responseToken?: string) {
    return api.post(
      `${BASE_URL}/${token}/submit/`, { response_token: responseToken }
    );
  },
};

export default PublicSurveyApi;
