/**
 * app.js — Point d'entrée : auth check → login ou feed.
 */

import { getAuthStatus, login, logout } from "./api.js";
import { loadFeed, setupProgressBar } from "./feed.js";
import { buildCalendarBtn, showToast } from "./ui.js";

// ── Auth ──────────────────────────────────────────────────────────

const loginScreen = document.getElementById("login-screen");
const appScreen = document.getElementById("app-screen");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const btnLogout = document.getElementById("btn-logout");

async function init() {
  const { authenticated } = await getAuthStatus();
  if (authenticated) {
    showApp();
  } else {
    showLogin();
  }
}

function showLogin() {
  loginScreen.classList.remove("hidden");
  appScreen.classList.add("hidden");
}

function showApp() {
  loginScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
  startApp();
}

loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const pwd = document.getElementById("login-password").value;
  loginError.textContent = "";
  const { ok, data } = await login(pwd);
  if (ok) {
    showApp();
  } else {
    loginError.textContent = data.message || "Mot de passe incorrect";
  }
});

btnLogout?.addEventListener("click", async () => {
  await logout();
  showLogin();
});

// Session expirée depuis l'API
window.addEventListener("auth:expired", showLogin);

// ── App ───────────────────────────────────────────────────────────

function startApp() {
  loadFeed("today");

  // Vérification sur le DOM — le flag module se reset au rechargement de page,
  // le DOM est la seule source de vérité fiable entre login/logout.
  if (document.getElementById("btn-calendar")) return;

  setupProgressBar();

  const actions = document.getElementById("top-bar-actions");
  const calBtn = buildCalendarBtn((date) => {
    loadFeed(date);
    showToast(`Fil du ${date}`);
  });
  actions?.insertBefore(calBtn, actions.firstChild);
}

init();
