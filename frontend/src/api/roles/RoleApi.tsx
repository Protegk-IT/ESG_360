import api from "@/services/api";

import type {
  Role,
  RoleFormData,
  Permission,
} from "@/types/role";

const BASE_URL = "/accounts/roles";

const RoleApi = {
  /* ==========================================================
     GET ALL ROLES
  ========================================================== */

  getAll() {
    return api.get<Role[]>(`${BASE_URL}/`);
  },

  /* ==========================================================
     GET ROLE BY ID
  ========================================================== */

  getById(id: number | string) {
    return api.get<Role>(
      `${BASE_URL}/${id}/`
    );
  },

  /* ==========================================================
     CREATE ROLE
  ========================================================== */

  create(data: RoleFormData) {
    return api.post(
      `${BASE_URL}/`,
      data
    );
  },

  /* ==========================================================
     UPDATE ROLE
  ========================================================== */

  update(
    id: number | string,
    data: RoleFormData
  ) {
    return api.put(
      `${BASE_URL}/${id}/`,
      data
    );
  },

  /* ==========================================================
     DELETE ROLE
  ========================================================== */

  delete(id: number | string) {
    return api.delete(
      `${BASE_URL}/${id}/`
    );
  },

  /* ==========================================================
     GET ROLE PERMISSION MATRIX
  ========================================================== */

  getPermissionMatrix() {
    return api.get<Permission[]>(
      "/accounts/permissions/"
    );
  },
};

export default RoleApi;