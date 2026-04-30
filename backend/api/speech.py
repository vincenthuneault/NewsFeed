"""Route POST /api/speech/transcribe — Google Cloud Speech-to-Text V2."""

from __future__ import annotations

import base64
import json
import os

from flask import Blueprint, jsonify, request
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

speech_bp = Blueprint("speech", __name__)


def _project_id() -> str:
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds:
        with open(creds) as f:
            return json.load(f).get("project_id", "")
    return ""


@speech_bp.route("/speech/transcribe", methods=["POST"])
def transcribe():
    """Transcrit un enregistrement audio en texte fr-CA (Google STT V2).

    Body JSON : {"audio": "<base64>", "mime_type": "..."}
    Réponse   : {"transcript": "texte reconnu"}

    AutoDetectDecodingConfig : aucun besoin de spécifier l'encodage
    ou le sample rate — Google les détecte depuis les headers du fichier.
    Modèle latest_long : meilleure précision pour le fr-CA.
    """
    data      = request.get_json(silent=True) or {}
    audio_b64 = data.get("audio", "")

    if not audio_b64:
        return jsonify({"error": True, "message": "audio requis", "code": "BAD_REQUEST"}), 400

    try:
        audio_bytes = base64.b64decode(audio_b64)
        project     = _project_id()
        recognizer  = f"projects/{project}/locations/global/recognizers/_"

        client = SpeechClient()
        resp   = client.recognize(request=cloud_speech.RecognizeRequest(
            recognizer=recognizer,
            config=cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=["fr-CA"],
                model="latest_long",
            ),
            content=audio_bytes,
        ))

        transcript = " ".join(
            r.alternatives[0].transcript
            for r in resp.results
            if r.alternatives
        )
        return jsonify({"transcript": transcript})

    except Exception as exc:
        return jsonify({"error": True, "message": str(exc), "code": "SERVER_ERROR"}), 500
