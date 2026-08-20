import api from "@/services/api";

import type { Module } from "@/types/datapoint";

const BASE_URL = "/modules";

const ModuleApi = {
  /* ==========================================================
     GET ENABLED MODULES
  ========================================================== */

  getEnabled() {
    return api.get<Module[]>(
      `${BASE_URL}/?enabled=true`
    );
  },

  /* ==========================================================
     GET ALL MODULES
  ========================================================== */

  getAll() {
    return api.get<Module[]>(
      `${BASE_URL}/`
    );
  },

  /* ==========================================================
     GET MODULE BY ID
  ========================================================== */

  getById(id: string) {
    return api.get<Module>(
      `${BASE_URL}/${id}/`
    );
  },
};

export default ModuleApi;