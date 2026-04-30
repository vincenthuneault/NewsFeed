/**
 * speech.js — Version minimale : start → enregistre → stop → envoie UNE FOIS.
 * Aucun timer, aucun chunk automatique, aucune logique de découpe.
 */


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
          if (e.data.size > 0) chunks.push(e.data);
        };

        recorder.onstop = async () => {
          cancelAnimationFrame(rafId); rafId = null;
          ctx?.close(); ctx = null;
          onAudioLevel?.(0);
          stream.getTracks().forEach(t => t.stop());
          _active = false;

          const blob = new Blob(chunks, { type: mime });

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
            const resp = await fetch("/api/speech/transcribe", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ audio: b64, mime_type: mime }),
            });
            if (resp.ok) {
              const data = await resp.json();
              if (data.transcript) onTranscript(data.transcript);
            }
          } catch { } finally {
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

        recorder.start();
        _active = true;

      } catch (err) {
        _active = false;
        onError(err.name === "NotAllowedError"
          ? "Microphone refusé — autorisez-le dans les paramètres du navigateur"
          : "Impossible d'accéder au microphone");
      }
    },

    stop() {
      if (!_active || !recorder) return Promise.resolve();
      return new Promise(res => {
        _resolve = res;
        recorder.stop();
      });
    },
  };
}
