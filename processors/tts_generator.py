"""Processeur TTS — génère des MP3 via Google Cloud Text-to-Speech."""

from __future__ import annotations

import hashlib
from pathlib import Path

from google.cloud import texttospeech

from core.logger import get_logger
from core.models import RawNewsItem
from processors.base_processor import BaseProcessor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_ROOT / "static" / "audio"

# ~150 mots/min en français ≈ 750 chars/min → 60s ≈ 750 chars
_MAX_CHARS = 700


class TTSGenerator(BaseProcessor):
    """Génère des fichiers audio MP3 à partir du résumé français."""

    def __init__(self, config: dict) -> None:
        super().__init__("tts_generator", config)
        self._log = get_logger("processors.tts_generator", config.get("logging"))
        tts = config.get("tts", {})
        self._client = texttospeech.TextToSpeechClient()
        self._voice = texttospeech.VoiceSelectionParams(
            language_code=tts.get("language_code", "fr-CA"),
            name=tts.get("voice_name", "fr-CA-Wavenet-A"),
        )
        self._audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
        )
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

        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=self._voice,
            audio_config=self._audio_config,
        )
        dest.write_bytes(response.audio_content)
        return str(dest.relative_to(PROJECT_ROOT))
