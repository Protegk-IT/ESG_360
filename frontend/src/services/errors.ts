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
            errors?: Record<string, string[] | string>;
          };
        };
      }
    ).response;

    const data = response?.data;

    // Prefer backend's main message
    if (data?.message) {
      return data.message;
    }

    // Otherwise use field-level errors
    if (data?.errors) {
      const messages = Object.values(data.errors)
        .flatMap((value) =>
          Array.isArray(value) ? value : [value],
        )
        .filter(Boolean);

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