"""Agent RSS générique — collecte n'importe quel feed RSS/Atom."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import requests

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0)"}
_TIMEOUT = 15


def _parse_date(entry: Any) -> datetime:
    """Extrait la date de publication d'une entrée feedparser."""
    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
    # feedparser peut fournir published_parsed (struct_time UTC)
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def _extract_image(entry: Any) -> str | None:
    """Tente d'extraire l'URL d'image d'une entrée RSS."""
    # media:content ou media:thumbnail
    for media in getattr(entry, "media_content", []):
        if media.get("url"):
            return media["url"]
    for thumb in getattr(entry, "media_thumbnail", []):
        if thumb.get("url"):
            return thumb["url"]
    # Enclosures (podcasts, etc.)
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href")
    return None


class RSSAgent(BaseAgent):
    """Collecte les nouvelles d'un ensemble de feeds RSS pour une catégorie."""

    def __init__(self, category: str, feeds: list[dict], config: dict) -> None:
        super().__init__(f"rss_{category}", config)
        self._category = category
        self._feeds = feeds  # [{"url": ..., "name": ...}, ...]
        self._log = get_logger(f"agents.rss_{category}", config.get("logging"))
        self._max_age_hours: int = config.get("rss", {}).get("max_age_hours", 48)
        self._max_per_feed: int = config.get("rss", {}).get("max_per_feed", 10)

    def collect(self) -> list[RawNewsItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._max_age_hours)
        items: list[RawNewsItem] = []

        for feed_cfg in self._feeds:
            url = feed_cfg.get("url", "")
            source_name = feed_cfg.get("name", url)
            try:
                feed_items = self._fetch_feed(url, source_name, cutoff)
                items.extend(feed_items)
                self._log.info(
                    "Feed RSS collecté",
                    extra={"agent": self.name, "source": source_name, "items": len(feed_items)},
                )
            except Exception as exc:
                self._log.warning(
                    "Feed RSS échoué",
                    extra={"agent": self.name, "source": source_name, "error": str(exc)},
                )

        self._log.info(
            "Collecte RSS terminée",
            extra={"agent": self.name, "category": self._category, "total": len(items)},
        )
        return items

    def _fetch_feed(self, url: str, source_name: str, cutoff: datetime) -> list[RawNewsItem]:
        parsed = feedparser.parse(url, request_headers=_HEADERS)

        if parsed.get("bozo") and not parsed.get("entries"):
            raise ValueError(f"Feed invalide : {parsed.get('bozo_exception', 'erreur inconnue')}")

        items: list[RawNewsItem] = []
        for entry in parsed.entries[: self._max_per_feed]:
            published = _parse_date(entry)
            if published < cutoff:
                continue

            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            description = getattr(entry, "summary", None) or getattr(entry, "description", None)
            if description:
                # Nettoyer les balises HTML basiques
                import re
                description = re.sub(r"<[^>]+>", " ", description).strip()[:500]

            items.append(
                RawNewsItem(
                    title=title,
                    source_url=link,
                    source_name=source_name,
                    category=self._category,
                    published_at=published,
                    description=description,
                    image_url=_extract_image(entry),
                    raw_content=description,
                )
            )
        return items

    @classmethod
    def from_config(cls, config: dict) -> list["RSSAgent"]:
        """Crée un agent RSS par catégorie depuis config.yaml."""
        agents = []
        feeds_by_category = config.get("rss", {}).get("feeds", {})
        for category, feeds in feeds_by_category.items():
            agents.append(cls(category, feeds, config))
        return agents
