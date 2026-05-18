"""Gate technique — filtre les articles inutilisables avant la summarisation."""

from __future__ import annotations

from urllib.parse import urlparse

from core.logger import get_logger
from processors.base_processor import BaseProcessor


class ContentGate(BaseProcessor):
    """Rejette silencieusement les articles qui ne peuvent pas être summarisés correctement.

    Trois critères de rejet :
    1. raw_content trop court (paywall, article vide)
    2. Domaine blacklisté (sources systématiquement inutilisables)
    3. Pattern de titre indiquant un live stream

    Les articles rejetés sont logués mais ne lèvent pas d'exception —
    le pipeline continue avec les articles restants.
    """

    def __init__(self, config: dict) -> None:
        super().__init__("content_gate", config)
        self._log = get_logger("processors.content_gate", config.get("logging"))
        gate = config.get("content_gate", {})
        self._min_chars: int = gate.get("min_raw_content_chars", 300)
        self._blacklisted: set[str] = set(gate.get("blacklisted_domains", []))
        self._title_patterns: list[str] = gate.get("title_patterns_rejected", [])

    def process(self, items: list) -> list:
        accepted = []
        rejected_count = 0

        for item in items:
            reason = self._reject_reason(item)
            if reason:
                self._log.info(
                    "Article rejeté par gate technique",
                    extra={
                        "processor": self.name,
                        "url": getattr(item, "source_url", ""),
                        "reason": reason,
                    },
                )
                rejected_count += 1
            else:
                accepted.append(item)

        if rejected_count:
            self._log.info(
                "Gate technique — résultat",
                extra={
                    "processor": self.name,
                    "candidats": len(items),
                    "acceptés": len(accepted),
                    "rejetés": rejected_count,
                },
            )

        return accepted

    def _reject_reason(self, item) -> str | None:
        # Contenu trop court
        raw = getattr(item, "raw_content", None) or ""
        if len(raw) < self._min_chars:
            return f"raw_content trop court ({len(raw)} chars < {self._min_chars})"

        # Domaine blacklisté
        url = getattr(item, "source_url", "") or ""
        try:
            domain = urlparse(url).netloc.lstrip("www.")
            if any(domain == bl or domain.endswith("." + bl) for bl in self._blacklisted):
                return f"domaine blacklisté : {domain}"
        except Exception:
            pass

        # Pattern live stream dans le titre
        title = getattr(item, "title", "") or ""
        for pattern in self._title_patterns:
            if pattern in title:
                return f"pattern live stream détecté : {pattern!r}"

        return None
