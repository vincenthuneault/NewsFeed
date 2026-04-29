/**
 * feed.js — Chargement du fil, scroll, navigation, compteur.
 */

import { getFeedToday, getFeedByDate } from "./api.js";
import { buildCard } from "./ui.js";
import { activateVideoPlayer, deactivateVideoPlayer, stopCurrentAudio } from "./player.js";

const feedEl = document.getElementById("feed");
const counterEl = document.getElementById("counter");
const loadingEl = document.getElementById("loading");
const errorEl = document.getElementById("error");

let _currentItems = [];
let _activeItem = null;
let _scrollObserver = null;

/** Retourne l'article actuellement visible à l'écran. */
export function getActiveItem() { return _activeItem; }

export async function loadFeed(date = "today") {
  showLoading();
  try {
    const data = date === "today" ? await getFeedToday() : await getFeedByDate(date);
    hideLoading();
    if (!data.items?.length) { showError("Aucune nouvelle disponible."); return; }
    renderCards(data.items);
  } catch (err) {
    showError(`Impossible de charger le fil : ${err.message}`);
  }
}

export function renderCards(items) {
  _currentItems = items;
  _activeItem = items[0] ?? null;
  if (_scrollObserver) _scrollObserver.disconnect();
  feedEl.innerHTML = "";

  items.forEach((item, idx) => feedEl.appendChild(buildCard(item, idx)));

  counterEl.textContent = `1 / ${items.length}`;
  _setupScrollObserver(items);
}

function _setupScrollObserver(items) {
  _scrollObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const idx = parseInt(entry.target.dataset.index, 10);
        const item = items[idx];
        if (!item) return;

        if (entry.isIntersecting) {
          _activeItem = item;
          counterEl.textContent = `${idx + 1} / ${items.length}`;
          if (item.video_type === "short") activateVideoPlayer(entry.target, item);
        } else {
          stopCurrentAudio();
          if (item.video_type === "short") deactivateVideoPlayer(entry.target, item);
        }
      });
    },
    { root: feedEl, threshold: 0.55 }
  );
  feedEl.querySelectorAll(".card").forEach((c) => _scrollObserver.observe(c));
}

export function setupProgressBar() {
  const bar = document.getElementById("progress-bar");
  if (!bar) return;
  feedEl.addEventListener("scroll", () => {
    if (!feedEl.scrollHeight || !_currentItems.length) return;
    const ratio = feedEl.scrollTop / (feedEl.scrollHeight - feedEl.clientHeight);
    bar.style.width = `${Math.min(100, ratio * 100)}%`;
  }, { passive: true });
}

function showLoading() {
  loadingEl?.classList.remove("hidden");
  errorEl?.classList.add("hidden");
  feedEl.innerHTML = "";
}

function hideLoading() { loadingEl?.classList.add("hidden"); }

export function showError(msg) {
  loadingEl?.classList.add("hidden");
  if (errorEl) { errorEl.classList.remove("hidden"); errorEl.textContent = msg; }
}
