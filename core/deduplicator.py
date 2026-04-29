"""Déduplication des nouvelles — URL exacte + titre flou (rapidfuzz)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from rapidfuzz import fuzz

from core.logger import get_logger
from core.models import RawNewsItem

_DEFAULT_THRESHOLD = 80
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
}


def _normalize_url(url: str) -> str:
    """Supprime les paramètres de tracking et normalise l'URL."""
    try:
        parsed = urlparse(url.lower().strip())
        params = {k: v for k, v in parse_qs(parsed.query).items() if k not in _TRACKING_PARAMS}
        clean = parsed._replace(query=urlencode(params, doseq=True), fragment="")
        return urlunparse(clean)
    except Exception:
        return url.lower().strip()


class Deduplicator:
    """Supprime les doublons exacts (URL) et flous (titre similaire)."""

    def __init__(self, config: dict) -> None:
        self._log = get_logger("core.deduplicator", config.get("logging"))
        dedup = config.get("deduplication", {})
        self._threshold: int = dedup.get("fuzzy_threshold", _DEFAULT_THRESHOLD)
        self._max_ratio: float = dedup.get("max_duplicate_ratio", 0.30)

    def deduplicate(self, items: list[RawNewsItem]) -> list[RawNewsItem]:
        if not items:
            return []

        before = len(items)
        seen_urls: set[str] = set()
        seen_titles: list[str] = []
        unique: list[RawNewsItem] = []

        for item in items:
            norm_url = _normalize_url(item.source_url)

            # Déduplication exacte par URL
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

            # Déduplication floue par titre
            title = item.title.strip().lower()
            if self._is_duplicate_title(title, seen_titles):
                continue
            seen_titles.append(title)
            unique.append(item)

        removed = before - len(unique)
        ratio = removed / before if before > 0 else 0

        self._log.info(
            "Déduplication terminée",
            extra={
                "avant": before,
                "après": len(unique),
                "doublons": removed,
                "ratio": f"{ratio:.0%}",
            },
        )

        if ratio > self._max_ratio:
            self._log.warning(
                "Taux de doublons élevé — sources trop similaires",
                extra={"ratio": f"{ratio:.0%}", "seuil": f"{self._max_ratio:.0%}"},
            )

        return unique

    def _is_duplicate_title(self, title: str, seen: list[str]) -> bool:
        for existing in seen:
            if fuzz.token_set_ratio(title, existing) >= self._threshold:
                return True
        return False
