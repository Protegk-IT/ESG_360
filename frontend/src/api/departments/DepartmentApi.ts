import api from "@/services/api";

import type {
  Department,
  DepartmentFormData,
} from "@/types/department";

const DepartmentApi = {
  // ==========================
  // Department CRUD
  // ==========================

  getAll() {
    return api.get<Department[]>(
      "/company/departments/"
    );
  },

  getById(id: number | string) {
    return api.get<Department>(
      `/company/departments/${id}/`
    );
  },

  create(data: DepartmentFormData) {
    return api.post(
      "/company/departments/",
      data
    );
  },

  update(
    id: number | string,
    data: DepartmentFormData
  ) {
    return api.put(
      `/company/departments/${id}/`,
      data
    );
  },

  patch(
    id: number | string,
    data: Partial<DepartmentFormData>
  ) {
    return api.patch(
      `/company/departments/${id}/`,
      data
    );
  },

  delete(id: number | string) {
    return api.delete(
      `/company/departments/${id}/`
    );
  },

  // ==========================
  // Master Data
  // ==========================

  getCompanies() {
    return api.get(
      "/company/companies/"
    );
  },

  getParentDepartments() {
    return api.get<Department[]>(
      "/company/departments/"
    );
  },
};

export default DepartmentApi;