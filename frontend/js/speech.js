/**
 * speech.js — Enregistrement vocal par segments VAD + Google STT.
 *
 * Pourquoi stop/start par segment plutôt que timeslice ?
 * MediaRecorder.start(N) produit des blobs de continuation après le premier :
 * ils n'ont pas les headers WebM → Google STT ne peut pas les décoder.
 * Chaque nouvelle instance MediaRecorder produit un fichier standalone valide.
 *
 * Callbacks :
 *   onTranscript(text)   — texte accumulé à chaque segment transcrit
 *   onStop(text)         — texte final à l'arrêt complet
 *   onError(msg)         — erreur micro ou réseau
 *   onAudioLevel(0..1)   — amplitude RMS ~60fps pendant l'enregistrement
 *   onPending(bool)      — true pendant l'attente de l'API Google STT
 */

export const voiceSupported = !!(
  navigator.mediaDevices?.getUserMedia &&
  window.MediaRecorder
);

// ── Paramètres VAD ───────────────────────────────────────────────────
const SILENCE_THRESHOLD  = 0.04;   // RMS en dessous = silence (0..1)
const SILENCE_DURATION   = 900;    // ms de silence → fin de segment
const MAX_SEGMENT_MS     = 8000;   // découpe forcée à 8s
const MIN_BLOB_BYTES     = 1000;   // ignore les blobs trop petits (< 1 KB)

export function createVoiceRecorder({ onTranscript, onStop, onError, onAudioLevel, onPending }) {
  let stream          = null;
  let audioCtx        = null;
  let rafId           = null;
  let confirmed       = "";
  let _recording      = false;
  let _pending        = 0;

  // État par segment
  let currentRecorder = null;
  let segmentChunks   = [];
  let segmentStartMs  = 0;
  let silenceStartMs  = null;
  let wasSpeaking     = false;

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/ogg;codecs=opus";

  // ── Cycle de vie des segments ─────────────────────────────────────

  function _startSegment() {
    segmentChunks  = [];
    segmentStartMs = Date.now();
    wasSpeaking    = false;
    silenceStartMs = null;

    currentRecorder = new MediaRecorder(stream, { mimeType });

    currentRecorder.addEventListener("dataavailable", (e) => {
      if (e.data.size > 0) segmentChunks.push(e.data);
    });

    currentRecorder.addEventListener("stop", () => {
      const blob = new Blob(segmentChunks, { type: mimeType });
      if (blob.size >= MIN_BLOB_BYTES) _sendChunk(blob);
    });

    currentRecorder.start();
  }

  function _endSegment(restart = false) {
    if (!currentRecorder || currentRecorder.state !== "recording") return;
    currentRecorder.stop();
    currentRecorder = null;
    if (restart && _recording) setTimeout(_startSegment, 40);
  }

  // ── AnalyserNode + boucle VAD ─────────────────────────────────────

  function _startAnalyser() {
    audioCtx = new AudioContext();
    const source   = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    function tick() {
      analyser.getByteFrequencyData(data);
      const rms = Math.sqrt(data.reduce((s, v) => s + v * v, 0) / data.length) / 255;
      onAudioLevel?.(rms);

      if (_recording && currentRecorder?.state === "recording") {
        const now        = Date.now();
        const segmentAge = now - segmentStartMs;

        if (rms > SILENCE_THRESHOLD) {
          wasSpeaking    = true;
          silenceStartMs = null;
          if (segmentAge > MAX_SEGMENT_MS) _endSegment(true);
        } else if (wasSpeaking) {
          if (!silenceStartMs) silenceStartMs = now;
          if (now - silenceStartMs >= SILENCE_DURATION) _endSegment(true);
        }
      }

      rafId = requestAnimationFrame(tick);
    }
    rafId = requestAnimationFrame(tick);
  }

  function _stopAnalyser() {
    cancelAnimationFrame(rafId);
    rafId = null;
    audioCtx?.close();
    audioCtx = null;
    onAudioLevel?.(0);
  }

  // ── Envoi à Google STT ────────────────────────────────────────────

  async function _sendChunk(blob) {
    _pending++;
    if (_pending === 1) onPending?.(true);
    try {
      const b64 = await _blobToBase64(blob);
      const res = await fetch("/api/speech/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: b64, mime_type: mimeType }),
      });
      if (!res.ok) return;
      const { transcript } = await res.json();
      if (transcript) {
        confirmed = (confirmed + " " + transcript).trim();
        onTranscript(confirmed);
      }
    } catch { /* erreur réseau — on continue */ } finally {
      _pending--;
      if (_pending === 0) onPending?.(false);
    }
  }

  // ── Interface publique ────────────────────────────────────────────

  return {
    get isRecording() { return _recording; },

    async start() {
      try {
        stream     = await navigator.mediaDevices.getUserMedia({ audio: true });
        _recording = true;
        confirmed  = "";
        _startAnalyser();
        _startSegment();
      } catch (err) {
        _recording = false;
        onError(
          err.name === "NotAllowedError"
            ? "Microphone refusé — autorisez-le dans les paramètres du navigateur"
            : "Impossible d'accéder au microphone"
        );
      }
    },

    stop() {
      if (!_recording) return;
      _recording = false;
      _stopAnalyser();
      _endSegment(false);
      setTimeout(() => {
        stream?.getTracks().forEach((t) => t.stop());
        onStop(confirmed);
      }, 200);
    },
  };
}

function _blobToBase64(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.readAsDataURL(blob);
  });
}
