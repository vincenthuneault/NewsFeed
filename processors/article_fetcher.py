"""Processeur de fetch d'article — enrichit raw_content avec le texte complet de la page.

Pour chaque RawNewsItem, tente de télécharger et d'extraire le contenu principal de
l'article via trafilatura. Si le texte extrait est plus riche que la description RSS,
raw_content est remplacé. Sinon, raw_content est conservé tel quel.

Les URLs YouTube/vidéo sont ignorées — pas de texte d'article à extraire.
L'extraction se fait en parallèle (ThreadPoolExecutor) pour limiter la latence.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
import trafilatura

from core.logger import get_logger
from core.models import RawNewsItem
from processors.base_processor import BaseProcessor

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
}

# Domaines sans texte d'article à fetcher (vidéo, apps, événements structurés, etc.)
_SKIP_DOMAINS = {
    "youtube.com", "youtu.be",
    "twitter.com", "x.com",
    "instagram.com", "tiktok.com",
    "facebook.com",
    "ticketmaster.ca", "ticketmaster.com",  # raw_content déjà construit par TicketmasterAgent
}


def _should_skip(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lstrip("www.")
        return any(domain == d or domain.endswith("." + d) for d in _SKIP_DOMAINS)
    except Exception:
        return False


def _fetch_article_text(url: str, timeout: int) -> str | None:
    """Télécharge et extrait le texte principal d'un article via trafilatura."""
    try:
        response = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        text = trafilatura.extract(
            response.text,
            url=url,
            favor_precision=True,   # Précision > rappel — évite de prendre le nav/pubs
            include_comments=False,
            include_tables=False,
            deduplicate=True,
        )
        return text
    except Exception:
        return None


class ArticleFetcher(BaseProcessor):
    """Enrichit raw_content avec le texte complet de l'article (via trafilatura).

    Position dans le pipeline : avant ContentGate et Summarizer.
    Permet au ContentGate de détecter les vrais paywalls, et au Summarizer
    de travailler sur le contenu réel plutôt que le court extrait RSS.
    """

    def __init__(self, config: dict) -> None:
        super().__init__("article_fetcher", config)
        self._log = get_logger("processors.article_fetcher", config.get("logging"))
        af = config.get("article_fetcher", {})
        self._timeout: int = af.get("timeout_seconds", 10)
        self._max_workers: int = af.get("max_workers", 8)
        self._max_chars: int = af.get("max_content_chars", 8000)  # Tronquer avant de passer au Summarizer

    def process(self, items: list[RawNewsItem]) -> list[RawNewsItem]:
        if not items:
            return items

        enriched = 0
        skipped = 0
        failed = 0

        # Fetch en parallèle
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._enrich, item): item
                for item in items
            }
            for future in as_completed(futures):
                result = future.result()
                if result == "enriched":
                    enriched += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1

        self._log.info(
            "Article fetch terminé",
            extra={
                "processor": self.name,
                "total": len(items),
                "enrichis": enriched,
                "ignorés": skipped,
                "échecs": failed,
            },
        )
        return items

    def _enrich(self, item: RawNewsItem) -> str:
        """Tente d'enrichir raw_content d'un item. Retourne 'enriched'/'skipped'/'failed'."""
        if _should_skip(item.source_url):
            return "skipped"

        text = _fetch_article_text(item.source_url, self._timeout)

        if not text or len(text) < 100:
            return "failed"

        # Tronquer pour ne pas dépasser le contexte du Summarizer
        text = text[: self._max_chars]

        existing_len = len(item.raw_content or "")
        if len(text) > existing_len:
            item.raw_content = text
            self._log.info(
                "Article enrichi",
                extra={
                    "processor": self.name,
                    "url": item.source_url[:80],
                    "avant": existing_len,
                    "après": len(text),
                },
            )
            return "enriched"

        return "failed"
