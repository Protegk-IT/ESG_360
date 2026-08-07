import api, { clearCsrfToken } from "@/services/api";

export async function logoutUser() {
    await api.post("/accounts/logout/");

    clearCsrfToken();
}