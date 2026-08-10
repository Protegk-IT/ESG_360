import axios from "axios";
import { toast } from "sonner";

let csrfToken = "";

// Global logout handler (registered by AuthContext)
let logoutHandler: (() => void) | null = null;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
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
    config.headers["X-CSRFToken"] = csrfToken;
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
    const isAuthBootstrapRequest = ["/accounts/login/", "/accounts/me/"].includes(
      error.config?.url ?? ""
    );

    switch (status) {
      case 401:
        if (isAuthBootstrapRequest) break;
        clearCsrfToken();

        // Clear auth state through AuthContext
        logoutHandler?.();

        toast.error("Your session has expired. Please login again.");

        // Avoid redirect loop
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }

        break;

      case 403:
        if (isAuthBootstrapRequest) break;
        toast.error("You don't have permission to perform this action.");
        break;

      case 404:
        toast.error("Requested resource not found or inaccessible.");
        break;

      case 500:
        toast.error("Something went wrong. Please try again.");
        break;
    }

    return Promise.reject(error);
  }
);

export default api;
