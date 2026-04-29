/**
 * api.js — Wrapper fetch centralisé.
 * Toutes les requêtes API passent par ici pour gérer les 401 uniformément.
 */

export async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (res.status === 401) {
    // Session expirée → retour au login
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new Error("Session expirée");
  }

  return res;
}

export async function getFeedToday() {
  const res = await apiFetch("/api/feed/today");
  if (!res.ok) throw new Error((await res.json()).message || `HTTP ${res.status}`);
  return res.json();
}

export async function getFeedByDate(date) {
  const res = await apiFetch(`/api/feed/${date}`);
  if (!res.ok) throw new Error((await res.json()).message || `HTTP ${res.status}`);
  return res.json();
}

export async function getFeedDates() {
  const res = await apiFetch("/api/feed/dates");
  if (!res.ok) return { dates: [] };
  return res.json();
}

export async function postFeedback(newsId, action) {
  const res = await apiFetch(`/api/news/${newsId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getAuthStatus() {
  const res = await fetch("/api/auth/status");
  return res.json();
}

export async function login(password) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  return { ok: res.ok, data: await res.json() };
}

export async function logout() {
  await fetch("/api/auth/logout", { method: "POST" });
}
