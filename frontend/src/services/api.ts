import axios from "axios";

let csrfToken = "";

const api = axios.create({
    baseURL: "http://localhost:8000/api",
    withCredentials: true,
    headers: {
        "Content-Type": "application/json",
    },
});

export function setCsrfToken(token: string) {
    csrfToken = token;
}

api.interceptors.request.use((config) => {
    if (csrfToken) {
        config.headers["X-CSRFToken"] = csrfToken;
    }

    return config;
});

export default api;
