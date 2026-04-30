/**
 * speech.js — Version minimale : start → enregistre → stop → envoie UNE FOIS.
 * Aucun timer, aucun chunk automatique, aucune logique de découpe.
 */

console.log("[speech.js] v1.7.10 chargé — aucun timer, aucun chunk automatique");

export const voiceSupported = !!(
  navigator.mediaDevices?.getUserMedia &&
  window.MediaRecorder
);

export function createVoiceRecorder({ onTranscript, onDone, onError, onAudioLevel, onPending }) {
  let stream   = null;
  let recorder = null;
  let chunks   = [];
  let ctx      = null;
  let rafId    = null;
  let _resolve = null;
  let _active  = false;

  const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/ogg;codecs=opus";

  return {
    get isRecording() { return _active; },
    get isBusy()      { return false; },

    async start() {
      if (_active) return;
      chunks = [];
      console.log("[mic] start");

      try {
        stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream, { mimeType: mime });

        recorder.ondataavailable = (e) => {
          console.log("[mic] dataavailable bytes=", e.data.size);
          if (e.data.size > 0) chunks.push(e.data);
        };

        recorder.onstop = async () => {
          console.log("[mic] onstop — envoi à Google STT");
          cancelAnimationFrame(rafId); rafId = null;
          ctx?.close(); ctx = null;
          onAudioLevel?.(0);
          stream.getTracks().forEach(t => t.stop());
          _active = false;

          const blob = new Blob(chunks, { type: mime });
          console.log("[mic] blob total bytes=", blob.size);

          if (blob.size < 100) {
            onDone?.(); _resolve?.(); _resolve = null; return;
          }

          onPending?.(true);
          try {
            const b64 = await new Promise(res => {
              const fr = new FileReader();
              fr.onloadend = () => res(fr.result.split(",")[1]);
              fr.readAsDataURL(blob);
            });
            console.log("[mic] b64 length=", b64.length, "— POST /api/speech/transcribe");
            const resp = await fetch("/api/speech/transcribe", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ audio: b64, mime_type: mime }),
            });
            console.log("[mic] réponse HTTP", resp.status);
            if (resp.ok) {
              const data = await resp.json();
              console.log("[mic] transcript=", data.transcript);
              if (data.transcript) onTranscript(data.transcript);
            }
          } catch (err) {
            console.error("[mic] erreur fetch:", err);
          } finally {
            onPending?.(false);
            onDone?.();
            _resolve?.(); _resolve = null;
          }
        };

        // Amplitude visualizer
        ctx = new AudioContext();
        const src = ctx.createMediaStreamSource(stream);
        const ana = ctx.createAnalyser();
        ana.fftSize = 64;
        src.connect(ana);
        const buf = new Uint8Array(ana.frequencyBinCount);
        const tick = () => {
          ana.getByteFrequencyData(buf);
          const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length) / 255;
          onAudioLevel?.(rms);
          rafId = requestAnimationFrame(tick);
        };
        rafId = requestAnimationFrame(tick);

        recorder.start(); // ← PAS de timeslice, enregistrement continu
        _active = true;
        console.log("[mic] enregistrement actif, mimeType=", mime);

      } catch (err) {
        console.error("[mic] erreur start:", err.name, err.message);
        _active = false;
        onError(err.name === "NotAllowedError"
          ? "Microphone refusé — autorisez-le dans les paramètres du navigateur"
          : "Impossible d'accéder au microphone");
      }
    },

    stop() {
      console.log("[mic] stop(), _active=", _active);
      if (!_active || !recorder) return Promise.resolve();
      return new Promise(res => {
        _resolve = res;
        recorder.stop();
      });
    },
  };
}
