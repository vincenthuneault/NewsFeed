/**
 * player.js — Lecteur YouTube inline (Shorts) + audio TTS.
 */

let _currentAudio = null;
let _currentAudioBtn = null;

// ── TTS Audio ─────────────────────────────────────────────────────

export function buildAudioBar(item) {
  const bar = document.createElement("div");
  bar.className = "card__audio";

  const btn = document.createElement("button");
  btn.className = "btn-play";
  btn.setAttribute("aria-label", "Écouter le résumé");
  btn.textContent = "▶";

  const label = document.createElement("span");
  label.className = "audio-label";
  label.textContent = "Écouter le résumé";

  const audio = new Audio(item.audio_path);

  btn.addEventListener("click", () => {
    stopCurrentAudio();
    if (audio.paused) {
      audio.play();
      btn.textContent = "⏸";
      _currentAudio = audio;
      _currentAudioBtn = btn;
    } else {
      audio.pause();
      btn.textContent = "▶";
      _currentAudio = null;
      _currentAudioBtn = null;
    }
  });

  audio.addEventListener("ended", () => {
    btn.textContent = "▶";
    _currentAudio = null;
    _currentAudioBtn = null;
  });

  bar.appendChild(btn);
  bar.appendChild(label);
  return bar;
}

export function stopCurrentAudio() {
  if (_currentAudio) {
    _currentAudio.pause();
    _currentAudio.currentTime = 0;
    if (_currentAudioBtn) _currentAudioBtn.textContent = "▶";
    _currentAudio = null;
    _currentAudioBtn = null;
  }
}

// ── YouTube inline ────────────────────────────────────────────────

/**
 * Remplace l'image d'une carte Short par un iframe YouTube muet en autoplay.
 * Appelé quand la carte entre dans le viewport.
 */
export function activateVideoPlayer(cardEl, item) {
  if (!item.video_url || item.video_type !== "short") return;

  const existing = cardEl.querySelector(".yt-player");
  if (existing) return; // déjà activé

  const videoId = _extractVideoId(item.video_url);
  if (!videoId) return;

  const iframe = document.createElement("iframe");
  iframe.className = "card__image yt-player";
  iframe.allow = "autoplay; fullscreen";
  iframe.allowFullscreen = true;
  iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1&loop=1&playlist=${videoId}&controls=1&modestbranding=1&rel=0`;

  const img = cardEl.querySelector(".card__image:not(.card__image--placeholder)");
  if (img) img.replaceWith(iframe);
}

/**
 * Supprime le player et restaure l'image pour économiser des ressources.
 */
export function deactivateVideoPlayer(cardEl, item) {
  const iframe = cardEl.querySelector(".yt-player");
  if (!iframe) return;

  // Stopper la vidéo en modifiant le src
  iframe.src = "";

  if (item.image_path || item.image_url) {
    const img = document.createElement("img");
    img.className = "card__image";
    img.src = item.image_path || item.image_url;
    img.alt = item.title || "";
    img.loading = "lazy";
    img.onerror = () => img.classList.add("card__image--placeholder");
    iframe.replaceWith(img);
  } else {
    iframe.remove();
  }
}

function _extractVideoId(url) {
  if (!url) return null;
  const m = url.match(/(?:v=|\/embed\/|\/shorts\/|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : null;
}
