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

  updateStakeholder(
    assessmentId: string,
    stakeholderId: string,
    data: Partial<StakeholderFormData>
  ) {
    return api.patch<Stakeholder>(
      `${BASE_URL}/${assessmentId}/stakeholders/${stakeholderId}/`,
      data
    );
  },

  deleteStakeholder(assessmentId: string, stakeholderId: string) {
    return api.delete(`${BASE_URL}/${assessmentId}/stakeholders/${stakeholderId}/`);
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

  downloadTemplate(assessmentId: string) {
    return api.get(
      `${BASE_URL}/${assessmentId}/stakeholder-import-template/`,
      { responseType: "blob" }
    );
  },
};

export default StakeholderApi;
