/**
 * app.js — Point d'entrée : auth check → login ou feed.
 */

import { getAuthStatus, login, logout } from "./api.js";
import { loadFeed, setupProgressBar, getActiveItem } from "./feed.js";
import { buildMainMenu, showToast } from "./ui.js";

const loginScreen = document.getElementById("login-screen");
const appScreen   = document.getElementById("app-screen");
const loginForm   = document.getElementById("login-form");
const loginError  = document.getElementById("login-error");

async function init() {
  const { authenticated } = await getAuthStatus();
  authenticated ? showApp() : showLogin();
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
  ok ? showApp() : (loginError.textContent = data.message || "Mot de passe incorrect");
});

window.addEventListener("auth:expired", showLogin);

// ── App ───────────────────────────────────────────────────────────

function startApp() {
  loadFeed("today");

  // Initialise l'UI une seule fois — vérifie la présence du bouton dans le DOM
  if (document.getElementById("btn-menu")) return;

  setupProgressBar();

  // Bouton ⋮ unique dans #top-bar-actions
  const actions = document.getElementById("top-bar-actions");
  const menuBtn = buildMainMenu({
    getActiveItem,
    onDateSelected: (date) => loadFeed(date),
    onLogout: async () => {
      await logout();
      showLogin();
    },
  });
  actions?.appendChild(menuBtn);
}

init();
