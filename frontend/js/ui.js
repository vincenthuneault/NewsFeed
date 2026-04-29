/**
 * ui.js — Construction des cartes, menu options, toast, calendrier.
 */

import { postFeedback, getFeedDates } from "./api.js";
import { buildAudioBar, activateVideoPlayer, deactivateVideoPlayer, stopCurrentAudio } from "./player.js";

// ── Toast ─────────────────────────────────────────────────────────

const _toast = document.createElement("div");
_toast.className = "feedback-toast";
document.body.appendChild(_toast);
let _toastTimer = null;

export function showToast(msg) {
  _toast.textContent = msg;
  _toast.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => _toast.classList.remove("show"), 2200);
}

// ── Card builder ──────────────────────────────────────────────────

export function buildCard(item, idx) {
  const div = document.createElement("div");
  div.className = "card";
  div.dataset.index = idx;
  div.dataset.id = item.id;
  div.dataset.videoType = item.video_type || "";

  // Image / vidéo longue overlay
  _appendMedia(div, item, idx);

  // Bouton options
  div.appendChild(_buildOptionsBtn(item));

  // Body
  const body = document.createElement("div");
  body.className = "card__body";

  const meta = document.createElement("div");
  meta.className = "card__meta";
  meta.innerHTML = `<span class="card__source">${_esc(item.source_name)}</span>`;
  if (item.category) meta.innerHTML += `<span>· ${_esc(item.category)}</span>`;
  body.appendChild(meta);

  const title = document.createElement("h2");
  title.className = "card__title";
  title.textContent = item.title;
  body.appendChild(title);

  const summary = document.createElement("p");
  summary.className = "card__summary";
  summary.textContent = item.summary_fr || item.description || "";
  body.appendChild(summary);

  if (item.source_url) {
    const link = document.createElement("a");
    link.className = "card__link";
    link.href = item.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.video_type === "long" ? "▶ Voir sur YouTube ↗" : "Voir la source ↗";
    body.appendChild(link);
  }

  div.appendChild(body);

  if (item.audio_path) div.appendChild(buildAudioBar(item));

  return div;
}

function _appendMedia(cardEl, item, idx) {
  // Shorts → image pour l'instant, player.js l'active au scroll
  // Long → image avec overlay "Voir sur YouTube"
  if (item.image_path || item.image_url) {
    const img = document.createElement("img");
    img.className = "card__image";
    img.src = item.image_path || item.image_url;
    img.alt = item.title;
    img.loading = idx === 0 ? "eager" : "lazy";
    img.onerror = () => img.replaceWith(_placeholder());
    cardEl.appendChild(img);
  } else {
    cardEl.appendChild(_placeholder());
  }

  // Overlay play pour les longues vidéos
  if (item.video_type === "long" && item.video_url) {
    const overlay = document.createElement("a");
    overlay.className = "video-overlay";
    overlay.href = item.video_url;
    overlay.target = "_blank";
    overlay.rel = "noopener noreferrer";
    overlay.innerHTML = `<span class="video-play-icon">▶</span>`;
    cardEl.appendChild(overlay);
  }
}

function _placeholder() {
  const el = document.createElement("div");
  el.className = "card__image card__image--placeholder";
  el.textContent = "📰";
  return el;
}

// ── Options menu ──────────────────────────────────────────────────

function _buildOptionsBtn(item) {
  const btn = document.createElement("button");
  btn.className = "btn-options";
  btn.setAttribute("aria-label", "Options");
  btn.textContent = "⋮";

  const panel = _buildFeedbackPanel(item);
  btn.after(panel); // sera ajouté à la carte par l'appelant

  // On attache le panel au même parent que le btn
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    document.querySelectorAll(".feedback-panel:not(.hidden)").forEach((p) => {
      if (p !== panel) p.classList.add("hidden");
    });
    panel.classList.toggle("hidden");
  });

  // Wrapper pour qu'ils soient tous les deux dans la carte
  const wrap = document.createDocumentFragment();
  wrap.appendChild(btn);
  wrap.appendChild(panel);
  return wrap;
}

function _buildFeedbackPanel(item) {
  const panel = document.createElement("div");
  panel.className = "feedback-panel hidden";

  const actions = [
    { action: "like",    label: "J'aime",         icon: "👍" },
    { action: "dislike", label: "Je n'aime pas",   icon: "👎" },
    { action: "skip",    label: "Ignorer",          icon: "⏭" },
  ];

  if (item.source_url) {
    const link = document.createElement("a");
    link.className = "btn-feedback panel-link";
    link.href = item.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.innerHTML = `<span>🔗</span><span>Source</span>`;
    panel.appendChild(link);
  }

  actions.forEach(({ action, label, icon }) => {
    const btn = document.createElement("button");
    btn.className = "btn-feedback";
    btn.innerHTML = `<span>${icon}</span><span>${label}</span>`;
    btn.addEventListener("click", async () => {
      try {
        await postFeedback(item.id, action);
        panel.classList.add("hidden");
        panel.querySelectorAll(".btn-feedback").forEach((b) =>
          b.classList.remove("active-like", "active-dislike")
        );
        if (action === "like") btn.classList.add("active-like");
        if (action === "dislike") btn.classList.add("active-dislike");
        showToast({ like: "👍 Aimé", dislike: "👎 Noté", skip: "⏭ Ignoré" }[action]);
      } catch {
        showToast("Erreur");
      }
    });
    panel.appendChild(btn);
  });

  document.addEventListener("click", () => panel.classList.add("hidden"), { passive: true });
  return panel;
}

// ── Calendrier ────────────────────────────────────────────────────

export function buildCalendarBtn(onDateSelected) {
  const btn = document.createElement("button");
  btn.id = "btn-calendar";
  btn.className = "btn-calendar";
  btn.setAttribute("aria-label", "Historique");
  btn.textContent = "📅";

  const modal = _buildCalendarModal(onDateSelected, btn);
  document.body.appendChild(modal);

  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    await _populateCalendar(modal, onDateSelected);
    modal.classList.toggle("hidden");
  });

  document.addEventListener("click", () => modal.classList.add("hidden"), { passive: true });
  return btn;
}

function _buildCalendarModal(onDateSelected, triggerBtn) {
  const modal = document.createElement("div");
  modal.className = "calendar-modal hidden";
  modal.addEventListener("click", (e) => e.stopPropagation());
  return modal;
}

async function _populateCalendar(modal, onDateSelected) {
  modal.innerHTML = `<div class="calendar-title">📅 Historique</div>`;
  try {
    const { dates } = await getFeedDates();
    if (!dates.length) {
      modal.innerHTML += `<p class="calendar-empty">Aucun fil disponible</p>`;
      return;
    }
    dates.forEach(({ date, count }) => {
      const btn = document.createElement("button");
      btn.className = "calendar-date";
      const label = date === new Date().toISOString().slice(0, 10) ? `Aujourd'hui` : date;
      btn.textContent = `${label}  (${count})`;
      btn.addEventListener("click", () => {
        modal.classList.add("hidden");
        onDateSelected(date);
      });
      modal.appendChild(btn);
    });
  } catch {
    modal.innerHTML += `<p class="calendar-empty">Erreur de chargement</p>`;
  }
}

// ── Utils ─────────────────────────────────────────────────────────

function _esc(str) {
  return (str || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
