import api from "@/services/api";

import type {
  StakeholderGroup,
  StakeholderGroupFormData,
  Stakeholder,
  StakeholderFormData,
} from "@/types/materiality/stakeholder";

const BASE_URL = "/materiality/assessments";

const StakeholderApi = {
  /* ========================================================
     STAKEHOLDER GROUPS
  ======================================================== */

  getGroups(assessmentId: string) {
    return api.get<StakeholderGroup[]>(
      `${BASE_URL}/${assessmentId}/groups/`
    );
  },

  createGroup(
    assessmentId: string,
    data: StakeholderGroupFormData
  ) {
    return api.post<StakeholderGroup>(
      `${BASE_URL}/${assessmentId}/groups/`,
      data
    );
  },

  /* ========================================================
     STAKEHOLDERS
  ======================================================== */

  getStakeholders(assessmentId: string) {
    return api.get<Stakeholder[]>(
      `${BASE_URL}/${assessmentId}/stakeholders/`
    );
  },

  createStakeholder(
    assessmentId: string,
    data: StakeholderFormData
  ) {
    return api.post<Stakeholder>(
      `${BASE_URL}/${assessmentId}/stakeholders/`,
      data
    );
  },

  /* ========================================================
     CSV IMPORT
  ======================================================== */

  importStakeholders(
    assessmentId: string,
    file: File
  ) {
    const formData = new FormData();

    formData.append("file", file);

    return api.post(
      `${BASE_URL}/${assessmentId}/stakeholders/import/`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
  },
};

export default StakeholderApi;