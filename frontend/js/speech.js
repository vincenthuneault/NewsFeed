/**
 * speech.js — Push-to-talk avec auto-découpe toutes les 55s.
 *
 * Google STT synchrone accepte max 60s. On découpe en segments de 55s :
 * chaque segment est un nouveau MediaRecorder (blob complet avec headers)
 * envoyé indépendamment pendant que l'enregistrement continue.
 *
 * Callbacks :
 *   onTranscript(text)  — nouveau texte (à appender au textarea)
 *   onDone()            — tout terminé (transcriptions + enregistrement)
 *   onError(msg)        — erreur micro
 *   onAudioLevel(0..1)  — amplitude pendant l'enregistrement
 *   onPending(bool)     — true quand un chunk est en transit vers Google
 */

export const voiceSupported = !!(
  navigator.mediaDevices?.getUserMedia &&
  window.MediaRecorder
);

const CHUNK_MS  = 55_000;  // 55s — sous la limite de 60s de Google STT
const MIN_BYTES = 500;

export function createVoiceRecorder({ onTranscript, onDone, onError, onAudioLevel, onPending }) {
  let stream          = null;
  let audioCtx        = null;
  let rafId           = null;
  let currentRecorder = null;
  let segmentChunks   = [];
  let chunkTimer      = null;
  let _recording      = false;
  let _pending        = 0;
  let _doneResolve    = null;

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/ogg;codecs=opus";

  // ── Chunk ─────────────────────────────────────────────────────────

  function _startChunk() {
    segmentChunks   = [];
    currentRecorder = new MediaRecorder(stream, { mimeType });

    currentRecorder.addEventListener("dataavailable", (e) => {
      if (e.data.size > 0) segmentChunks.push(e.data);
    });

    currentRecorder.addEventListener("stop", () => {
      clearTimeout(chunkTimer);
      const blob = new Blob(segmentChunks, { type: mimeType });

      if (!_recording) stream?.getTracks().forEach((t) => t.stop());

      if (blob.size >= MIN_BYTES) {
        _sendChunk(blob);
      } else if (!_recording && _pending === 0) {
        onDone?.();
        _doneResolve?.(); _doneResolve = null;
      }

      if (_recording) _startChunk();
    });

    currentRecorder.start();

    chunkTimer = setTimeout(() => {
      if (_recording && currentRecorder?.state === "recording") {
        currentRecorder.stop();
      }
    }, CHUNK_MS);
  }

  // ── Analyser ──────────────────────────────────────────────────────

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
      rafId = requestAnimationFrame(tick);
    }
    rafId = requestAnimationFrame(tick);
  }

  function _stopAnalyser() {
    cancelAnimationFrame(rafId); rafId = null;
    audioCtx?.close(); audioCtx = null;
    onAudioLevel?.(0);
  }

  // ── Envoi Google STT ──────────────────────────────────────────────

  async function _sendChunk(blob) {
    _pending++;
    onPending?.(true);
    try {
      const b64 = await _blobToBase64(blob);
      const res = await fetch("/api/speech/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: b64, mime_type: mimeType }),
      });
      if (res.ok) {
        const { transcript } = await res.json();
        if (transcript) onTranscript(transcript);
      }
    } catch { } finally {
      _pending--;
      onPending?.(_pending > 0);
      if (_pending === 0 && !_recording) {
        onDone?.();
        _doneResolve?.(); _doneResolve = null;
      }
    }
  }

  // ── Interface publique ────────────────────────────────────────────

  return {
    get isRecording() { return _recording; },
    get isBusy()      { return _pending > 0; },

    async start() {
      if (_recording || _pending > 0) return;
      try {
        stream     = await navigator.mediaDevices.getUserMedia({ audio: true });
        _recording = true;
        _startAnalyser();
        _startChunk();
      } catch (err) {
        _recording = false;
        onError(err.name === "NotAllowedError"
          ? "Microphone refusé — autorisez-le dans les paramètres du navigateur"
          : "Impossible d'accéder au microphone");
      }
    },

    stop() {
      if (!_recording) return Promise.resolve();
      _recording = false;
      clearTimeout(chunkTimer);
      _stopAnalyser();
      return new Promise((resolve) => {
        _doneResolve = resolve;
        if (currentRecorder?.state === "recording") {
          currentRecorder.stop();
        } else {
          stream?.getTracks().forEach((t) => t.stop());
          if (_pending === 0) { onDone?.(); resolve(); _doneResolve = null; }
        }
      });
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
