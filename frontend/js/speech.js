/**
 * speech.js — Enregistrement audio par chunks + transcription Google STT.
 *
 * Callbacks disponibles :
 *   onTranscript(text)   — texte accumulé à chaque chunk transcrit
 *   onStop(text)         — texte final une fois l'arrêt complet
 *   onError(msg)         — erreur micro ou réseau
 *   onAudioLevel(0..1)   — niveau d'amplitude ~20fps pendant l'enregistrement
 *   onPending(bool)      — true pendant l'attente de l'API, false à la réponse
 */

export const voiceSupported = !!(
  navigator.mediaDevices?.getUserMedia &&
  window.MediaRecorder
);

export function createVoiceRecorder({ onTranscript, onStop, onError, onAudioLevel, onPending }) {
  let mediaRecorder = null;
  let stream        = null;
  let audioCtx      = null;
  let rafId         = null;
  let confirmed     = "";
  let _recording    = false;
  let _pending      = 0;

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/ogg;codecs=opus";

  // ── Amplitude via Web Audio API ──────────────────────────────────
  function _startAnalyser(mediaStream) {
    audioCtx = new AudioContext();
    const source   = audioCtx.createMediaStreamSource(mediaStream);
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

  // ── Envoi d'un chunk ─────────────────────────────────────────────
  async function sendChunk(blob) {
    if (blob.size === 0) return;
    _pending++;
    onPending?.(true);
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
    } catch {
      // Erreur réseau sur un chunk — on continue
    } finally {
      _pending--;
      if (_pending === 0) onPending?.(false);
    }
  }

  // ── Interface publique ───────────────────────────────────────────
  return {
    get isRecording() { return _recording; },

    async start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType });
        confirmed = "";

        _startAnalyser(stream);

        mediaRecorder.addEventListener("dataavailable", (e) => sendChunk(e.data));
        mediaRecorder.addEventListener("stop", () => {
          _stopAnalyser();
          stream.getTracks().forEach((t) => t.stop());
          _recording = false;
          onStop(confirmed);
        });

        mediaRecorder.start(3000);
        _recording = true;
      } catch (err) {
        _recording = false;
        onError(err.name === "NotAllowedError" ? "Microphone non autorisé" : "Erreur microphone");
      }
    },

    stop() {
      if (!_recording || !mediaRecorder) return;
      mediaRecorder.stop();
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
