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

let _appStarted = false;

function startApp() {
  loadFeed("today");

  // N'initialise l'UI qu'une seule fois — évite les doublons au re-login
  if (_appStarted) return;
  _appStarted = true;

  setupProgressBar();

  // Bouton calendrier dans #top-bar-actions (à côté du logout)
  const actions = document.getElementById("top-bar-actions");
  const calBtn = buildCalendarBtn((date) => {
    loadFeed(date);
    showToast(`Fil du ${date}`);
  });
  actions?.insertBefore(calBtn, actions.firstChild);
}

init();
