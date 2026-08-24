import axios from "axios";

function firstMessage(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstMessage(item);
      if (message) return message;
    }
  }
  if (value && typeof value === "object") {
    for (const item of Object.values(value)) {
      const message = firstMessage(item);
      if (message) return message;
    }
  }
  return null;
}

/**
 * Read the backend's common `{ message, errors }` envelope while remaining
 * compatible with existing DRF `{ detail }` and field-error responses.
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback;

  const data = error.response?.data;
  if (typeof data === "string") return data;
  if (!data || typeof data !== "object") return error.message || fallback;

  if (typeof data.message === "string") return data.message;
  if (typeof data.detail === "string") return data.detail;

  return firstMessage(data.errors ?? data) ?? fallback;
}
