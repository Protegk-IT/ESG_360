import api from "@/services/api";

import type {
  ReportingPeriod,
  ReportingPeriodFormData,
  GenerateSubPeriodsPayload,
} from "@/types/reporting-period";

const ReportingPeriodApi = {
  // ==========================================================
  // CRUD
  // ==========================================================

  getAll() {
    return api.get<ReportingPeriod[]>(
      "/periods/"
    );
  },

  getById(id: string) {
    return api.get<ReportingPeriod>(
      `/periods/${id}/`
    );
  },

  create(
    data: ReportingPeriodFormData
  ) {
    return api.post(
      "/periods/",
      data
    );
  },

  update(
    id: string,
    data: ReportingPeriodFormData
  ) {
    return api.put(
      `/periods/${id}/`,
      data
    );
  },

  patch(
    id: string,
    data: Partial<ReportingPeriodFormData>
  ) {
    return api.patch(
      `/periods/${id}/`,
      data
    );
  },

  delete(id: string) {
    return api.delete(
      `/periods/${id}/`
    );
  },

  // ==========================================================
  // CUSTOM ACTIONS
  // ==========================================================

  getCurrent() {
    return api.get<ReportingPeriod>(
      "/periods/current/"
    );
  },

  lock(id: string) {
    return api.post<ReportingPeriod>(
      `/periods/${id}/lock/`,
      {}
    );
  },

  unlock(id: string) {
    return api.post<ReportingPeriod>(
      `/periods/${id}/unlock/`,
      {}
    );
  },

  generateSubPeriods(
    id: string,
    data: GenerateSubPeriodsPayload
  ) {
    return api.post(
      `/periods/${id}/generate-subperiods/`,
      data
    );
  },
};

export default ReportingPeriodApi;