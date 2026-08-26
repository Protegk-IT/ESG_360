import api from "@/services/api";

import type {
  ApiResponse,
  CreateDataRequestPayload,
  DataRequestDetail,
  DataRequestListItem,
  EvidenceFile,
  PaginatedResponse,
  ReasonPayload,
  ReassignDataRequestPayload,
  Submission,
  SubmissionHistory,
  TableRowWritePayload,
  TypedValueWritePayload,
} from "@/types/dataCapture";

const BASE_URL = "/data-capture";

const DataCaptureApi = {
  /* ========================================================
     DATA REQUESTS
  ======================================================== */

  getAll(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }) {
    return api.get<
      ApiResponse<PaginatedResponse<DataRequestListItem>>
    >(`${BASE_URL}/requests/`, {
      params,
    });
  },

  getMine(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }) {
    return api.get<
      ApiResponse<PaginatedResponse<DataRequestListItem>>
    >(`${BASE_URL}/requests/mine/`, {
      params,
    });
  },

  getById(id: string) {
    return api.get<ApiResponse<DataRequestDetail>>(
      `${BASE_URL}/requests/${id}/`,
    );
  },

  create(data: CreateDataRequestPayload) {
    return api.post<ApiResponse<DataRequestDetail>>(
      `${BASE_URL}/requests/`,
      data,
    );
  },

  reassign(
    id: string,
    data: ReassignDataRequestPayload,
  ) {
    return api.post<ApiResponse<DataRequestDetail>>(
      `${BASE_URL}/requests/${id}/reassign/`,
      data,
    );
  },

  /* ========================================================
     SUBMISSION
  ======================================================== */

  getSubmission(requestId: string) {
    return api.get<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/`,
    );
  },

  saveAnswer(
    requestId: string,
    data: TypedValueWritePayload,
  ) {
    return api.patch<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/answer/`,
      data,
    );
  },

  /* ========================================================
     TABLE ROWS
  ======================================================== */

  createTableRow(
    requestId: string,
    data: TableRowWritePayload,
  ) {
    return api.post<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/table-rows/`,
      data,
    );
  },

  updateTableRow(
    requestId: string,
    rowId: string,
    data: TableRowWritePayload,
  ) {
    return api.patch<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/table-rows/${rowId}/`,
      data,
    );
  },

  /* ========================================================
     HISTORY
  ======================================================== */

  getHistory(requestId: string) {
    return api.get<ApiResponse<SubmissionHistory>>(
      `${BASE_URL}/requests/${requestId}/submission/history/`,
    );
  },

  /* ========================================================
     EVIDENCE
  ======================================================== */

  getEvidence(
    requestId: string,
    params?: {
      page?: number;
      page_size?: number;
    },
  ) {
    return api.get<
      ApiResponse<PaginatedResponse<EvidenceFile>>
    >(`${BASE_URL}/requests/${requestId}/evidence/`, {
      params,
    });
  },

  uploadEvidence(
    requestId: string,
    data: FormData,
  ) {
    return api.post<ApiResponse<EvidenceFile>>(
      `${BASE_URL}/requests/${requestId}/evidence/`,
      data,
    );
  },

  getEvidenceById(
    requestId: string,
    evidenceId: string,
  ) {
    return api.get<ApiResponse<EvidenceFile>>(
      `${BASE_URL}/requests/${requestId}/evidence/${evidenceId}/`,
    );
  },

  deleteEvidence(
    requestId: string,
    evidenceId: string,
  ) {
    return api.delete(
      `${BASE_URL}/requests/${requestId}/evidence/${evidenceId}/`,
    );
  },

  downloadEvidence(
    requestId: string,
    evidenceId: string,
  ) {
    return api.get<Blob>(
      `${BASE_URL}/requests/${requestId}/evidence/${evidenceId}/download/`,
      {
        responseType: "blob",
      },
    );
  },

  /* ========================================================
     LIFECYCLE
  ======================================================== */

  submit(requestId: string) {
    return api.post<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/submit/`,
    );
  },

  approve(requestId: string) {
    return api.post<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/approve/`,
    );
  },

  reject(
    requestId: string,
    data: ReasonPayload,
  ) {
    return api.post<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/reject/`,
      data,
    );
  },

  reopen(
    requestId: string,
    data: ReasonPayload,
  ) {
    return api.post<ApiResponse<Submission>>(
      `${BASE_URL}/requests/${requestId}/submission/reopen/`,
      data,
    );
  },
};

export default DataCaptureApi;