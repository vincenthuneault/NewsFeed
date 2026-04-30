"""Route POST /api/speech/transcribe — Google Cloud Speech-to-Text fr-CA."""

from __future__ import annotations

import base64

from flask import Blueprint, jsonify, request
from google.cloud import speech

speech_bp = Blueprint("speech", __name__)

_ENCODING_MAP = {
    "webm": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
    "ogg":  speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
}


def _detect_encoding(mime_type: str):
    m = mime_type.lower()
    for key, enc in _ENCODING_MAP.items():
        if key in m:
            return enc
    return None


@speech_bp.route("/speech/transcribe", methods=["POST"])
def transcribe():
    """Transcrit un chunk audio en texte fr-CA.

    Body JSON : {"audio": "<base64>", "mime_type": "audio/webm;codecs=opus"}
    Réponse   : {"transcript": "texte reconnu"}
    """
    data = request.get_json(silent=True) or {}
    audio_b64 = data.get("audio", "")
    mime_type  = data.get("mime_type", "")

    if not audio_b64:
        return jsonify({"error": True, "message": "audio requis", "code": "BAD_REQUEST"}), 400

    encoding = _detect_encoding(mime_type)
    if not encoding:
        return jsonify({"error": True, "message": f"format non supporté : {mime_type}", "code": "BAD_REQUEST"}), 400

    try:
        audio_bytes = base64.b64decode(audio_b64)
        client = speech.SpeechClient()
        audio  = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=48000,
            language_code="fr-CA",
        )
        response = client.recognize(config=config, audio=audio)
        transcript = " ".join(
            r.alternatives[0].transcript
            for r in response.results
            if r.alternatives
        )
        return jsonify({"transcript": transcript})
    except Exception as exc:
        return jsonify({"error": True, "message": str(exc), "code": "SERVER_ERROR"}), 500
