import api from "@/services/api";

import type {
  OrgNode,
  OrgNodePayload,
} from "@/types/organization";

const OrganizationApi = {
  // ==========================
  // Organization CRUD
  // ==========================

  getAll(params?: {
    node_type?: string;
    parent?: string;
    is_active?: boolean;
    search?: string;
  }) {
    return api.get<OrgNode[]>(
      "/org/nodes/",
      {
        params,
      }
    );
  },

  getById(id: string | number) {
    return api.get<OrgNode>(
      `/org/nodes/${id}/`
    );
  },

  create(data: OrgNodePayload) {
    return api.post(
      "/org/nodes/",
      data
    );
  },

  update(
    id: string | number,
    data: OrgNodePayload
  ) {
    return api.put(
      `/org/nodes/${id}/`,
      data
    );
  },

  patch(
    id: string | number,
    data: Partial<OrgNodePayload>
  ) {
    return api.patch(
      `/org/nodes/${id}/`,
      data
    );
  },

  delete(id: string | number) {
    return api.delete(
      `/org/nodes/${id}/`
    );
  },

  // ==========================
  // Tree
  // ==========================

  getTree() {
    return api.get(
      "/org/tree/"
    );
  },

  getSubtree(
    id: string | number
  ) {
    return api.get(
      `/org/nodes/${id}/subtree/`
    );
  },

  getAncestors(
    id: string | number
  ) {
    return api.get(
      `/org/nodes/${id}/ancestors/`
    );
  },

  move(
    id: string | number,
    parent_id: string | null
  ) {
    return api.post(
      `/org/nodes/${id}/move/`,
      {
        parent_id,
      }
    );
  },
};

export default OrganizationApi;