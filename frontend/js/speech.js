/**
 * speech.js — Push-to-talk + Google STT.
 *
 * L'utilisateur maintient le bouton enfoncé pour enregistrer.
 * Au relâchement, le blob complet (headers WebM inclus) est envoyé
 * à Google STT en une seule requête.
 *
 * Callbacks :
 *   onTranscript(text)   — nouveau texte transcrit (à appender au textarea)
 *   onDone()             — transcription terminée (API a répondu)
 *   onError(msg)         — erreur micro ou réseau
 *   onAudioLevel(0..1)   — amplitude RMS ~60fps pendant l'enregistrement
 *   onPending(bool)      — true pendant l'attente de l'API Google STT
 */

export const voiceSupported = !!(
  navigator.mediaDevices?.getUserMedia &&
  window.MediaRecorder
);

export function createVoiceRecorder({ onTranscript, onDone, onError, onAudioLevel, onPending }) {
  let stream      = null;
  let audioCtx    = null;
  let rafId       = null;
  let recorder    = null;
  let chunks      = [];
  let _recording  = false;
  let _busy       = false;   // true pendant l'appel API (bloque un nouveau start)

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/ogg;codecs=opus";

  // ── Amplitude ─────────────────────────────────────────────────────

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
    cancelAnimationFrame(rafId);
    rafId = null;
    audioCtx?.close();
    audioCtx = null;
    onAudioLevel?.(0);
  }

  // ── Envoi ─────────────────────────────────────────────────────────

  async function _send(blob) {
    if (blob.size < 500) { onDone?.(); return; }
    _busy = true;
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
    } catch { /* erreur réseau silencieuse */ } finally {
      _busy = false;
      onPending?.(false);
      onDone?.();
    }
  }

  // ── Interface publique ────────────────────────────────────────────

  return {
    get isRecording() { return _recording; },
    get isBusy()      { return _busy; },

    async start() {
      if (_recording || _busy) return;
      try {
        stream  = await navigator.mediaDevices.getUserMedia({ audio: true });
        chunks  = [];
        recorder = new MediaRecorder(stream, { mimeType });

        recorder.addEventListener("dataavailable", (e) => {
          if (e.data.size > 0) chunks.push(e.data);
        });
        recorder.addEventListener("stop", () => {
          _stopAnalyser();
          stream.getTracks().forEach((t) => t.stop());
          _recording = false;
          _send(new Blob(chunks, { type: mimeType }));
        });

        _startAnalyser();
        recorder.start();
        _recording = true;
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
      if (!_recording || !recorder) return;
      recorder.stop();
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
