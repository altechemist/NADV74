// Thin fetch wrapper around the CSRMS API.
// It attaches the JWT access token to every call and, when the backend
// answers 401, tries one automatic refresh before giving up.

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

const ACCESS_KEY = "csrms_access_token";
const REFRESH_KEY = "csrms_refresh_token";

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  save(access, refresh) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

async function parseBody(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function refreshAccessToken() {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) {
    tokenStore.clear();
    return false;
  }

  const payload = await response.json();
  tokenStore.save(payload.access, payload.refresh);
  return true;
}

async function request(path, options = {}, allowRetry = true) {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  // An expired access token is refreshed once and the call retried.
  if (response.status === 401 && allowRetry && (await refreshAccessToken())) {
    return request(path, options, false);
  }

  const body = await parseBody(response);
  if (!response.ok) {
    const message =
      body && typeof body === "object" && "detail" in body
        ? String(body.detail)
        : `Request failed (${response.status})`;
    throw new ApiError(message, response.status, body);
  }
  return body;
}

export default request;
