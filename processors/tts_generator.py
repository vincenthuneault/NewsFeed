"""Processeur TTS — génère des MP3 via Google Cloud Text-to-Speech (Gemini 2.5 Pro)."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import google.auth.transport.requests
import google.oauth2.service_account

from core.logger import get_logger
from processors.base_processor import BaseProcessor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_ROOT / "static" / "audio"
_DEFAULT_CREDENTIALS = PROJECT_ROOT / "secrets" / "google_tts_credentials.json"
_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# ~150 mots/min en français ≈ 750 chars/min → 60s ≈ 750 chars
_MAX_CHARS = 700


class TTSGenerator(BaseProcessor):
    """Génère des fichiers audio MP3 à partir du résumé français."""

    def __init__(self, config: dict) -> None:
        super().__init__("tts_generator", config)
        self._log = get_logger("processors.tts_generator", config.get("logging"))
        tts = config.get("tts", {})

        creds_path = tts.get("credentials_path", str(_DEFAULT_CREDENTIALS))
        credentials = google.oauth2.service_account.Credentials.from_service_account_file(
            creds_path, scopes=_SCOPES
        )
        self._session = google.auth.transport.requests.AuthorizedSession(credentials)

        self._language_code = tts.get("language_code", "fr-CA")
        self._voice_name = tts.get("voice_name", "Achernar")
        self._model_name = tts.get("model_name", "gemini-2.5-pro-tts")
        self._tts_prompt = tts.get("tts_prompt", "")

        AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    def process(self, items: list) -> list:
        for item in items:
            text = item.summary_fr or item.description or item.title
            if not text:
                continue
            try:
                item.audio_path = self._generate(text, item.source_url)
                self._log.info(
                    "Audio généré",
                    extra={"processor": self.name, "path": item.audio_path},
                )
            except Exception as exc:
                self._log.error(
                    "TTS échoué",
                    extra={"processor": self.name, "error": str(exc)},
                )
        return items

    def _generate(self, text: str, source_url: str) -> str:
        text = text[:_MAX_CHARS]
        url_hash = hashlib.md5(source_url.encode()).hexdigest()[:16]
        dest = AUDIO_DIR / f"{url_hash}.mp3"

        if dest.exists():
            return str(dest.relative_to(PROJECT_ROOT))

        payload: dict = {
            "audioConfig": {"audioEncoding": "MP3"},
            "input": {"text": text},
            "voice": {
                "languageCode": self._language_code,
                "modelName": self._model_name,
                "name": self._voice_name,
            },
        }
        if self._tts_prompt:
            payload["input"]["prompt"] = self._tts_prompt

        response = self._session.post(_TTS_URL, json=payload)
        response.raise_for_status()

        audio_bytes = base64.b64decode(response.json()["audioContent"])
        dest.write_bytes(audio_bytes)
        return str(dest.relative_to(PROJECT_ROOT))
