const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  base: API_BASE,

  login: (username, password) =>
    fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then(handle),

  listUsers: () => fetch(`${API_BASE}/auth/users`).then(handle),

  me: () => fetch(`${API_BASE}/auth/me`, { headers: authHeaders() }).then(handle),

  listDrawings: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
    ).toString();
    return fetch(`${API_BASE}/drawings${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(),
    }).then(handle);
  },

  getDrawing: (id) =>
    fetch(`${API_BASE}/drawings/${id}`, { headers: authHeaders() }).then(handle),

  createDrawing: (title, file) => {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    return fetch(`${API_BASE}/drawings`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    }).then(handle);
  },

  addVersion: (drawingId, file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/drawings/${drawingId}/versions`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    }).then(handle);
  },

  submitDrawing: (drawingId) =>
    fetch(`${API_BASE}/drawings/${drawingId}/submit`, {
      method: "POST",
      headers: authHeaders(),
    }).then(handle),

  changeStatus: (drawingId, versionId, newStatus, note) =>
    fetch(`${API_BASE}/drawings/${drawingId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ version_id: versionId, new_status: newStatus, note }),
    }).then(handle),

  addComment: (versionId, payload) =>
    fetch(`${API_BASE}/versions/${versionId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    }).then(handle),

  resolveComment: (commentId) =>
    fetch(`${API_BASE}/comments/${commentId}/resolve`, {
      method: "POST",
      headers: authHeaders(),
    }).then(handle),

  listNotifications: () =>
    fetch(`${API_BASE}/notifications`, { headers: authHeaders() }).then(handle),

  markNotificationRead: (id) =>
    fetch(`${API_BASE}/notifications/${id}/read`, {
      method: "POST",
      headers: authHeaders(),
    }).then(handle),

  markAllNotificationsRead: () =>
    fetch(`${API_BASE}/notifications/read-all`, {
      method: "POST",
      headers: authHeaders(),
    }).then(handle),

  auditLog: (drawingId) =>
    fetch(`${API_BASE}/drawings/${drawingId}/audit-log`, {
      headers: authHeaders(),
    }).then(handle),

  fileUrl: (path) => `${API_BASE}${path}`,
};
