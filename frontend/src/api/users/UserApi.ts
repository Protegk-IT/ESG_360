import api from "@/services/api";
import type { UserData, UserFormData } from "@/types/user";

const UserApi = {
  // ==========================
  // User CRUD
  // ==========================

  getAll() {
    return api.get<UserData[]>("/accounts/users/");
  },

  getById(id: number | string) {
    return api.get<UserData>(`/accounts/users/${id}/`);
  },

  create(data: FormData) {
    return api.post("/accounts/users/", data, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  },

  update(id: number | string, data: FormData) {
    return api.put(`/accounts/users/${id}/`, data, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  },

  patch(
    id: number | string,
    data: Partial<UserFormData>
  ) {
    return api.patch(
      `/accounts/users/${id}/`,
      data
    );
  },

  delete(id: number | string) {
    return api.delete(
      `/accounts/users/${id}/`
    );
  },

  // ==========================
  // Master Data
  // ==========================

  getCompanies() {
    return api.get(
      "/company/profile/"
    );
  },

  getDepartments() {
    return api.get(
      "/company/departments/"
    );
  },

  // ==========================
// RBAC
// ==========================

getRoles() {
  return api.get("/accounts/roles/");
},

getOrganizationUnits() {
  return api.get("/org/nodes/");
},

getFacilities() {
  return api.get("/organizations/facilities/");
},
};

export default UserApi;