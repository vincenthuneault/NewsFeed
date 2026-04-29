"""Processeur de résumé IA — Claude Sonnet, français, max 4 phrases."""

from __future__ import annotations

import anthropic

from core.logger import get_logger
from core.models import RawNewsItem
from processors.base_processor import BaseProcessor

_SYSTEM_PROMPT = (
    "Tu es un journaliste qui résume des nouvelles en français québécois. "
    "Écris un résumé factuel de 2 à 4 phrases courtes et claires. "
    "N'invente rien. Si l'information est insuffisante, dis-le brièvement."
)


class Summarizer(BaseProcessor):
    """Génère des résumés en français via Claude."""

    def __init__(self, config: dict) -> None:
        super().__init__("summarizer", config)
        self._log = get_logger("processors.summarizer", config.get("logging"))
        claude = config.get("claude", {})
        self._client = anthropic.Anthropic(api_key=claude.get("api_key"))
        self._model: str = claude.get("model", "claude-sonnet-4-6")
        self._max_input: int = claude.get("max_input_tokens", 2000)
        self._max_output: int = claude.get("max_output_tokens", 300)
        self._temperature: float = claude.get("temperature", 0.3)

    def process(self, items: list) -> list:
        results = []
        for item in items:
            try:
                item.summary_fr = self._summarize(item)
                self._log.info(
                    "Résumé généré",
                    extra={"processor": self.name, "title": item.title[:60]},
                )
            except Exception as exc:
                self._log.error(
                    "Résumé échoué",
                    extra={"processor": self.name, "error": str(exc), "title": item.title[:60]},
                )
                item.summary_fr = item.description or item.title
            results.append(item)
        return results

    def _summarize(self, item: RawNewsItem) -> str:
        content_parts = [f"Titre : {item.title}"]
        if item.description:
            content_parts.append(f"Description : {item.description}")
        if item.raw_content:
            # Tronquer pour respecter max_input_tokens (~4 chars/token)
            max_chars = self._max_input * 3
            content_parts.append(f"Contenu : {item.raw_content[:max_chars]}")

        user_content = "\n".join(content_parts)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_output,
            temperature=self._temperature,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text.strip()
