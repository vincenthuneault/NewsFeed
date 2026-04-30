/**
 * ui.js — Construction des cartes (sans bouton par carte),
 *          menu principal fixe ⋮ (feedback + calendrier + logout).
 */

import { postFeedback, getFeedDates, postComment, postBugReport, getAppVersion } from "./api.js";
import { voiceSupported, createVoiceRecorder } from "./speech.js";
import { buildAudioBar } from "./player.js";

// ── Toast ─────────────────────────────────────────────────────────

const _toast = document.createElement("div");
_toast.className = "feedback-toast";
document.body.appendChild(_toast);
let _toastTimer = null;

export function showToast(msg, duration = 2200) {
  _toast.textContent = msg;
  _toast.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => _toast.classList.remove("show"), duration);
}

// ── Card (simple, sans bouton ⋮ par carte) ───────────────────────

export function buildCard(item, idx) {
  const div = document.createElement("div");
  div.className = "card";
  div.dataset.index = idx;
  div.dataset.id = item.id;
  div.dataset.videoType = item.video_type || "";

  _appendMedia(div, item, idx);

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

  div.appendChild(body);
  if (item.audio_path) div.appendChild(buildAudioBar(item));

  return div;
}

function _appendMedia(cardEl, item, idx) {
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

// ── Menu principal fixe ⋮ ────────────────────────────────────────
//
// Un seul bouton dans le coin supérieur droit de l'écran.
// Le contenu du menu dépend de l'article actif au moment de l'ouverture.

export function buildMainMenu({ getActiveItem, onDateSelected, onLogout }) {
  // Nettoyer une instance précédente
  document.getElementById("btn-menu")?.remove();
  document.getElementById("main-menu")?.remove();

  // Bouton ⋮
  const btn = document.createElement("button");
  btn.id = "btn-menu";
  btn.className = "btn-top";
  btn.setAttribute("aria-label", "Menu");
  btn.textContent = "⋮";

  // Menu
  const menu = document.createElement("div");
  menu.id = "main-menu";
  menu.className = "main-menu hidden";
  menu.addEventListener("click", (e) => e.stopPropagation());
  document.body.appendChild(menu);

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    _renderMenu(menu, getActiveItem(), onDateSelected, onLogout);
    menu.classList.toggle("hidden");
  });

  document.addEventListener("click", () => menu.classList.add("hidden"), { passive: true });

  return btn;
}

async function _renderMenu(menu, item, onDateSelected, onLogout) {
  menu.innerHTML = "";

  // ── En-tête : titre de l'article actif ──
  if (item) {
    const header = document.createElement("div");
    header.className = "menu-header";
    header.textContent = item.title.length > 55 ? item.title.slice(0, 52) + "…" : item.title;
    menu.appendChild(header);
    _menuDivider(menu);
  }

  // ── Feedback ──
  if (item) {
    const feedbackActions = [
      { action: "like",    icon: "👍", label: "J'aime" },
      { action: "dislike", icon: "👎", label: "Je n'aime pas" },
      { action: "skip",    icon: "⏭",  label: "Ignorer" },
    ];
    feedbackActions.forEach(({ action, icon, label }) => {
      menu.appendChild(_menuBtn(icon, label, async () => {
        try {
          await postFeedback(item.id, action);
          menu.classList.add("hidden");
          showToast({ like: "👍 Aimé", dislike: "👎 Noté", skip: "⏭ Ignoré" }[action]);
        } catch { showToast("Erreur"); }
      }));
    });

    // Lien source
    if (item.source_url) {
      const link = document.createElement("a");
      link.className = "menu-item menu-link";
      link.href = item.source_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.innerHTML = `<span>🔗</span><span>Voir la source</span>`;
      link.addEventListener("click", () => menu.classList.add("hidden"));
      menu.appendChild(link);
    }

    // ── Commentaire ──
    menu.appendChild(_buildInputSection({
      icon: "💬",
      label: "Commenter",
      placeholder: "Votre commentaire…",
      onSend: async (text) => {
        await postComment(item.id, text);
        menu.classList.add("hidden");
        showToast("💬 Commentaire enregistré");
      },
    }));

    _menuDivider(menu);
  }

  // ── Calendrier (dates disponibles inline) ──
  const calSection = document.createElement("div");
  calSection.className = "menu-cal-section";

  const calToggle = _menuBtn("📅", "Historique", () => {
    calDates.classList.toggle("hidden");
  });
  calSection.appendChild(calToggle);

  const calDates = document.createElement("div");
  calDates.className = "menu-cal-dates hidden";
  calSection.appendChild(calDates);
  menu.appendChild(calSection);

  // Charger les dates à la demande
  calToggle.addEventListener("click", async () => {
    if (!calDates.classList.contains("hidden") && calDates.children.length > 0) return;
    calDates.innerHTML = `<div class="menu-cal-loading">Chargement…</div>`;
    try {
      const { dates } = await getFeedDates();
      calDates.innerHTML = "";
      if (!dates.length) {
        calDates.innerHTML = `<div class="menu-cal-loading">Aucun fil disponible</div>`;
        return;
      }
      const today = new Date().toISOString().slice(0, 10);
      dates.forEach(({ date, count }) => {
        const d = _menuBtn(
          "",
          `${date === today ? "Aujourd'hui" : date}  (${count})`,
          () => {
            menu.classList.add("hidden");
            onDateSelected(date);
            showToast(`Fil du ${date}`);
          }
        );
        d.classList.add("menu-cal-date");
        calDates.appendChild(d);
      });
    } catch {
      calDates.innerHTML = `<div class="menu-cal-loading">Erreur</div>`;
    }
  }, { once: true });

  _menuDivider(menu);

  // ── Rapport de bug ──
  menu.appendChild(_buildInputSection({
    icon: "🐛",
    label: "Signaler un bug",
    placeholder: "Décrivez le problème…",
    onSend: async (text) => {
      const context = {
        article_id: item?.id ?? null,
        article_title: item?.title ?? null,
        user_agent: navigator.userAgent,
        timestamp: new Date().toISOString(),
      };
      await postBugReport(text, context);
      menu.classList.add("hidden");
      showToast("🐛 Bug signalé, merci !");
    },
  }));

  _menuDivider(menu);

  // ── Déconnexion ──
  menu.appendChild(_menuBtn("⎋", "Déconnexion", () => {
    menu.classList.add("hidden");
    onLogout();
  }));

  // ── Version ──
  const verEl = document.createElement("div");
  verEl.className = "menu-version";
  verEl.textContent = "…";
  menu.appendChild(verEl);
  getAppVersion().then((v) => { if (v) verEl.textContent = `v${v}`; });
}

function _menuBtn(icon, label, onClick) {
  const btn = document.createElement("button");
  btn.className = "menu-item";
  btn.innerHTML = icon ? `<span class="menu-icon">${icon}</span><span>${label}</span>` : `<span>${label}</span>`;
  btn.addEventListener("click", onClick);
  return btn;
}

function _menuDivider(parent) {
  const hr = document.createElement("div");
  hr.className = "menu-divider";
  parent.appendChild(hr);
}

function _buildInputSection({ icon, label, placeholder, onSend }) {
  const section = document.createElement("div");
  section.className = "menu-input-section";

  const area = document.createElement("div");
  area.className = "menu-textarea-wrapper hidden";

  const textarea = document.createElement("textarea");
  textarea.className = "menu-textarea";
  textarea.placeholder = placeholder;
  textarea.rows = 3;

  // ── Canvas d'amplitude ──
  const canvas = document.createElement("canvas");
  canvas.className = "voice-amplitude hidden";
  canvas.height = 36;
  const ampHistory = [];

  function drawAmplitude(level) {
    const W = canvas.width;
    const H = canvas.height;
    const BAR = 3, GAP = 1, SLOT = BAR + GAP;
    const maxBars = Math.floor(W / SLOT);

    ampHistory.push(level);
    if (ampHistory.length > maxBars) ampHistory.shift();

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, H);
    ampHistory.forEach((v, i) => {
      const barH = Math.max(2, v * H * 0.9);
      ctx.fillStyle = `rgba(79,142,247,${0.35 + v * 0.65})`;
      ctx.fillRect(i * SLOT, (H - barH) / 2, BAR, barH);
    });
  }

  // ── Indicateur d'attente API ──
  const pending = document.createElement("div");
  pending.className = "voice-pending hidden";
  pending.innerHTML = `<span class="voice-pending-dot"></span>Transcription…`;

  const btnRow = document.createElement("div");
  btnRow.className = "menu-textarea-actions";

  // ── Bouton micro (seulement si MediaRecorder disponible) ──
  let recorder = null;
  if (voiceSupported) {
    const micBtn = document.createElement("button");
    micBtn.className = "btn-mic";
    micBtn.type = "button";
    micBtn.title = "Dicter";
    micBtn.textContent = "🎤";

    recorder = createVoiceRecorder({
      onTranscript: (text) => {
        // Appende le nouveau segment au texte déjà dans le textarea
        const existing = textarea.value.trim();
        textarea.value = existing ? `${existing} ${text}` : text;
      },
      onDone: () => {
        micBtn.classList.remove("btn-mic--recording");
        canvas.classList.add("hidden");
        ampHistory.length = 0;
      },
      onError: (msg) => {
        micBtn.classList.remove("btn-mic--recording");
        micBtn.classList.add("btn-mic--error");
        micBtn.title = msg;
        canvas.classList.add("hidden");
        ampHistory.length = 0;
        showToast(msg, 4000);
        setTimeout(() => {
          micBtn.classList.remove("btn-mic--error");
          micBtn.title = "Maintenir pour dicter";
        }, 4000);
      },
      onAudioLevel: (level) => {
        if (canvas.width !== canvas.offsetWidth && canvas.offsetWidth > 0) {
          canvas.width = canvas.offsetWidth;
        }
        drawAmplitude(level);
      },
      onPending: (active) => pending.classList.toggle("hidden", !active),
    });

    micBtn.title = "Maintenir pour dicter";

    let _stopRequested = false;

    const _stopMic = () => {
      _stopRequested = true;
      if (recorder.isRecording) recorder.stop();
    };

    micBtn.addEventListener("pointerdown", async (e) => {
      e.preventDefault();
      if (recorder.isBusy) return;
      _stopRequested = false;
      micBtn.setPointerCapture(e.pointerId); // pointerup reçu même si le doigt glisse
      micBtn.classList.add("btn-mic--recording");
      canvas.classList.remove("hidden");
      await recorder.start();
      // getUserMedia peut être lent (dialogue permission) — si l'utilisateur
      // a déjà relâché pendant ce temps, on arrête immédiatement
      if (_stopRequested && recorder.isRecording) recorder.stop();
    });

    micBtn.addEventListener("pointerup",     _stopMic);
    micBtn.addEventListener("pointercancel", _stopMic);

    btnRow.appendChild(micBtn);
  }

  // ── Bouton Envoyer ──
  const sendBtn = document.createElement("button");
  sendBtn.className = "menu-send-btn";
  sendBtn.type = "button";
  sendBtn.textContent = "Envoyer";
  sendBtn.addEventListener("click", async () => {
    recorder?.stop();
    const text = textarea.value.trim();
    if (!text) return;
    sendBtn.disabled = true;
    try {
      await onSend(text);
    } catch {
      showToast("Erreur");
    } finally {
      sendBtn.disabled = false;
    }
  });

  btnRow.appendChild(sendBtn);
  area.appendChild(textarea);
  area.appendChild(canvas);
  area.appendChild(pending);
  area.appendChild(btnRow);

  const toggle = _menuBtn(icon, label, () => area.classList.toggle("hidden"));
  section.appendChild(toggle);
  section.appendChild(area);

  return section;
}

function _esc(str) {
  return (str || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
