function extractMessages(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(extractMessages);
  if (typeof value === "object" && value !== null) {
    return Object.values(value).flatMap(extractMessages);
  }
  return [];
}

export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  // Axios error
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response = (
      error as {
        response?: {
          data?: {
            message?: string;
            detail?: string;
            errors?: Record<string, unknown>;
          };
        };
      }
    ).response;

    const data = response?.data;

    // Prefer backend's main message
    if (data?.message) {
      return data.message;
    }

    // DRF's standard top-level error shape — permission denials,
    // auth failures, throttling, and generic APIException all
    // return { "detail": "..." } rather than "message".
    if (data?.detail) {
      return data.detail;
    }

    // Field-level errors, including nested serializer errors
    // (e.g. { field: { subfield: ["error"] } }), not just flat
    // { field: ["error"] } / { field: "error" }.
    if (data?.errors) {
      const messages = extractMessages(data.errors);

      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  }

  // Normal Error object
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}