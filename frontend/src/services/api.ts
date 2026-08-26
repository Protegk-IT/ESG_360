
import { toast } from "sonner";

let csrfToken = "";
let csrfTokenRequest: Promise<string> | null = null;
import axios, { AxiosHeaders } from "axios";

// Global logout handler (registered by AuthContext)
let logoutHandler: (() => void) | null = null;

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000/api",
  withCredentials: true,
});

// =========================
// CSRF
// =========================
export function setCsrfToken(token: string) {
  csrfToken = token;
}

export function clearCsrfToken() {
  csrfToken = "";
}

/**
 * Obtain a Django CSRF token before an unsafe request made from a public
 * route. This matters when a browser retains a valid session cookie across a
 * reload: DRF then correctly enforces CSRF even for the login endpoint.
 */
export async function ensureCsrfToken() {
  if (csrfToken) return csrfToken;

  if (!csrfTokenRequest) {
    csrfTokenRequest = api
      .get<{ csrfToken: string }>("/accounts/csrf/")
      .then((response) => {
        setCsrfToken(response.data.csrfToken);
        return response.data.csrfToken;
      })
      .finally(() => {
        csrfTokenRequest = null;
      });
  }

  return csrfTokenRequest;
}

// =========================
// Logout Handler
// =========================
export function registerLogoutHandler(handler: () => void) {
  logoutHandler = handler;
}

// =========================
// Request Interceptor
// =========================
api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase();

  // Attach CSRF only for unsafe requests
  if (
    csrfToken &&
    ["POST", "PUT", "PATCH", "DELETE"].includes(method ?? "")
  ) {
    config.headers = config.headers ?? new AxiosHeaders();
    config.headers["X-CSRFToken"] = csrfToken;
  }

  /*
   * IMPORTANT:
   * Do not set application/json for FormData requests.
   *
   * The browser/Axios must generate:
   * multipart/form-data; boundary=...
   *
   * Setting Content-Type manually would prevent the correct multipart
   * boundary from being generated.
   */
  if (config.data instanceof FormData) {
    if (config.headers) {
      delete config.headers["Content-Type"];
      delete config.headers["content-type"];
    }
  } else {
    /*
     * Preserve the existing JSON behavior for all normal API requests.
     */
    config.headers = config.headers ?? new AxiosHeaders();

    if (
      !config.headers["Content-Type"] &&
      !config.headers["content-type"]
    ) {
      config.headers["Content-Type"] = "application/json";
    }
  }

  return config;
});

// =========================
// Response Interceptor
// =========================
api.interceptors.response.use(
  (response) => response,

  (error) => {
    const status = error.response?.status;

    const isAuthBootstrapRequest = [
      "/accounts/login/",
      "/accounts/me/",
    ].includes(error.config?.url ?? "");

    switch (status) {
      case 401:
        if (isAuthBootstrapRequest) break;

        clearCsrfToken();

        // Clear auth state through AuthContext
        logoutHandler?.();

        toast.error(
          "Your session has expired. Please login again.",
        );

        // Avoid redirect loop
        if (window.location.pathname !== "/") {
          window.location.href = "/";
        }

        break;

      case 403:
        if (isAuthBootstrapRequest) break;

        toast.error(
          "You don't have permission to perform this action.",
        );

        break;

      // Feature pages own their 404/5xx presentation. A global toast makes
      // expected empty states (such as an unconfigured company profile) look
      // like failures and duplicates the page-level message.
    }

    return Promise.reject(error);
  },
);

export default api;