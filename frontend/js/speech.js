/**
 * speech.js — Enregistrement audio par chunks + transcription Google STT.
 *
 * Usage :
 *   import { voiceSupported, createVoiceRecorder } from "./speech.js";
 *   const rec = createVoiceRecorder({ onTranscript, onStop, onError });
 *   await rec.start();
 *   rec.stop();
 */

export const voiceSupported = !!(
  navigator.mediaDevices?.getUserMedia &&
  window.MediaRecorder
);

/**
 * Crée un enregistreur vocal.
 * @param {Object} callbacks
 * @param {(text: string) => void} callbacks.onTranscript  — appelé à chaque chunk transcrit (texte accumulé)
 * @param {(text: string) => void} callbacks.onStop        — appelé une fois l'arrêt complet (texte final)
 * @param {(msg:  string) => void} callbacks.onError       — appelé en cas d'erreur
 */
export function createVoiceRecorder({ onTranscript, onStop, onError }) {
  let mediaRecorder = null;
  let stream        = null;
  let confirmed     = "";
  let _recording    = false;

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/ogg;codecs=opus";

  async function sendChunk(blob) {
    if (blob.size === 0) return;
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
    }
  }

  return {
    get isRecording() { return _recording; },

    async start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType });
        confirmed = "";

        mediaRecorder.addEventListener("dataavailable", (e) => sendChunk(e.data));
        mediaRecorder.addEventListener("stop", () => {
          stream.getTracks().forEach((t) => t.stop());
          _recording = false;
          onStop(confirmed);
        });

        mediaRecorder.start(3000); // chunk toutes les 3 secondes
        _recording = true;
      } catch (err) {
        _recording = false;
        onError(err.name === "NotAllowedError" ? "Microphone non autorisé" : "Erreur microphone");
      }
    },

    stop() {
      if (!_recording || !mediaRecorder) return;
      mediaRecorder.stop(); // déclenche "dataavailable" (dernier chunk) puis "stop"
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
