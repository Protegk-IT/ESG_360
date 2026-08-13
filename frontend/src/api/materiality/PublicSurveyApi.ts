import api from "@/services/api";

import type {
  PublicSurveyGetResponse,
} from "@/types/materiality/survey";

const BASE_URL =
  "/public/materiality/survey";

const PublicSurveyApi = {
  getSurvey(token: string) {
    return api.get<PublicSurveyGetResponse>(
      `${BASE_URL}/${token}/`
    );
  },

  saveResponse(
    token: string,
    data: {
      question: string;
      value: number;
      comment?: string;
    }
  ) {
    return api.post(
      `${BASE_URL}/${token}/answer/`,
      data
    );
  },

  submitSurvey(token: string) {
    return api.post(
      `${BASE_URL}/${token}/submit/`
    );
  },
};

export default PublicSurveyApi;