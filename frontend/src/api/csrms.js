// One function per CSRMS endpoint so pages never build URLs by hand.
import request from "./client";

export const api = {
  // Auth
  login: (username, password) =>
    request("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) }),
  register: (payload) =>
    request("/auth/register/", { method: "POST", body: JSON.stringify(payload) }),
  logout: (refresh) =>
    request("/auth/logout/", { method: "POST", body: JSON.stringify({ refresh }) }, false),
  me: () => request("/auth/me/"),
  updateMe: (payload) => request("/auth/me/", { method: "PUT", body: JSON.stringify(payload) }),

  // Users (admin)
  users: () => request("/users/"),
  createUser: (payload) => request("/users/", { method: "POST", body: JSON.stringify(payload) }),
  deactivateUser: (id) => request(`/users/${id}/`, { method: "DELETE" }),

  // Categories
  categories: () => request("/categories/"),
  createCategory: (name) => request("/categories/", { method: "POST", body: JSON.stringify({ name }) }),

  // Requests
  requests: (query = "") => request(`/requests/${query ? `?${query}` : ""}`),
  requestDetail: (id) => request(`/requests/${id}/`),
  createRequest: (payload) =>
    request("/requests/", { method: "POST", body: JSON.stringify(payload) }),
  updateRequest: (id, payload, partial = true) =>
    request(`/requests/${id}/`, {
      method: partial ? "PATCH" : "PUT",
      body: JSON.stringify(payload),
    }),
  cancelRequest: (id) => request(`/requests/${id}/`, { method: "DELETE" }),
  setStatus: (id, status, comment = "") =>
    request(`/requests/${id}/status/`, {
      method: "PATCH",
      body: JSON.stringify({ status, comment }),
    }),
  assign: (id, assignedTo) =>
    request(`/requests/${id}/assign/`, {
      method: "POST",
      body: JSON.stringify({ assigned_to: assignedTo }),
    }),
  addComment: (id, comment) =>
    request(`/requests/${id}/updates/`, { method: "POST", body: JSON.stringify({ comment }) }),
  history: (id) => request(`/requests/${id}/history/`),

  // Telemetry
  telemetryHistory: (range = "live") => request(`/telemetry/history/?range=${range}`),

  // Dashboard and notifications
  dashboard: () => request("/dashboard/"),
  notifications: () => request("/notifications/"),
};
