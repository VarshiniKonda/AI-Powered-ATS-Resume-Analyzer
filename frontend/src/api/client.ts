import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") || "/api";
export const TOKEN_STORAGE_KEY = "ats_access_token";

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10_000,
});

api.interceptors.request.use((config) => {
  const token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item?.msg === "string" ? item.msg : "Invalid input"))
        .join(", ");
    }
    return error.message || "The request failed. Please try again.";
  }
  return error instanceof Error ? error.message : "The request failed. Please try again.";
}