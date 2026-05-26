"""Agent Sitemap générique — collecte des articles depuis des sitemaps XML.

Gère deux cas :
- Sitemap standard : liste d'URLs avec <loc> et <lastmod>
- Sitemap index : liste de sous-sitemaps à récurser (OpenAI, etc.)

Chaque source peut définir :
  url_filter     : filtre appliqué aux URLs d'articles (ex. "/news/")
  sitemap_filter : filtre appliqué aux URLs de sous-sitemaps dans un index (ex. "research")

Les titres sont extraits du slug d'URL — ArticleFetcher enrichit le contenu dans le pipeline.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from agents.base_agent import BaseAgent
from agents.rss_generic import _PROMPTS_BY_CATEGORY
from core.logger import get_logger
from core.models import RawNewsItem

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0)"}
_TIMEOUT = 15


class SitemapAgent(BaseAgent):
    """Collecte des articles depuis un ou plusieurs sitemaps XML pour une catégorie."""

    def __init__(
        self,
        category: str,
        sources: list[dict],
        config: dict,
        system_prompt: str = "",
    ) -> None:
        super().__init__(f"sitemap_{category}", config)
        self._category = category
        self._sources = sources
        self._log = get_logger(f"agents.sitemap_{category}", config.get("logging"))
        self._max_age_hours: int = config.get("rss", {}).get("max_age_hours", 48)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)
        self._max_per_source: int = (
            config.get("sitemap_sources", {}).get("max_per_source", 50)
        )
        self._system_prompt = system_prompt

    def collect(self) -> list[RawNewsItem]:
        raw = self._fetch_all_sources()

        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]
        if len(items) < len(raw):
            self._log.info(
                "URLs déjà soumises exclues",
                extra={"agent": self.name, "exclues": len(raw) - len(items)},
            )

        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            self._log.info("Aucun article frais en sitemap", extra={"agent": self.name})
            return []

        if self._system_prompt:
            return self._llm_select(items, self._system_prompt, self._category, self._max_items)
        return items[: self._max_items]

    # ------------------------------------------------------------------
    # Collecte
    # ------------------------------------------------------------------

    def _fetch_all_sources(self) -> list[RawNewsItem]:
        items: list[RawNewsItem] = []
        for source in self._sources:
            try:
                fetched = self._fetch_source(source)
                items.extend(fetched)
                self._log.info(
                    "Sitemap collecté",
                    extra={"agent": self.name, "source": source["name"], "items": len(fetched)},
                )
            except Exception as exc:
                self._log.warning(
                    "Sitemap échoué",
                    extra={"agent": self.name, "source": source["name"], "error": str(exc)},
                )
        return items

    def _fetch_source(self, source: dict) -> list[RawNewsItem]:
        resp = requests.get(source["url"], headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag == "sitemapindex":
            return self._parse_sitemap_index(root, source)
        return self._parse_sitemap(root, source)

    # ------------------------------------------------------------------
    # Sitemap index → récursion vers les sous-sitemaps
    # ------------------------------------------------------------------

    def _parse_sitemap_index(self, root: ET.Element, source: dict) -> list[RawNewsItem]:
        sitemap_filter: str | None = source.get("sitemap_filter")
        items: list[RawNewsItem] = []

        for child in root:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag != "sitemap":
                continue

            loc = self._get_child_text(child, "loc")
            if not loc:
                continue
            if sitemap_filter and sitemap_filter not in loc:
                continue

            try:
                resp = requests.get(loc, headers=_HEADERS, timeout=_TIMEOUT)
                resp.raise_for_status()
                sub_root = ET.fromstring(resp.content)
                items.extend(self._parse_sitemap(sub_root, source))
            except Exception as exc:
                self._log.warning(
                    "Sous-sitemap échoué",
                    extra={"agent": self.name, "url": loc, "error": str(exc)},
                )

        return items

    # ------------------------------------------------------------------
    # Sitemap standard → extraction des URLs d'articles
    # ------------------------------------------------------------------

    def _parse_sitemap(self, root: ET.Element, source: dict) -> list[RawNewsItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._max_age_hours)
        url_filter: str | None = source.get("url_filter")
        items: list[RawNewsItem] = []

        for url_el in root:
            url_tag = url_el.tag.split("}")[-1] if "}" in url_el.tag else url_el.tag
            if url_tag != "url":
                continue

            loc = self._get_child_text(url_el, "loc")
            lastmod = self._get_child_text(url_el, "lastmod")

            if not loc:
                continue
            if url_filter and url_filter not in loc:
                continue

            published_at = self._parse_lastmod(lastmod)
            if published_at is None or published_at < cutoff:
                continue

            items.append(
                RawNewsItem(
                    title=self._slug_to_title(loc),
                    source_url=loc,
                    source_name=source["name"],
                    category=self._category,
                    published_at=published_at,
                )
            )

            if len(items) >= self._max_per_source:
                break

        return items

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_child_text(element: ET.Element, tag: str) -> str | None:
        """Retourne le texte du premier enfant correspondant au tag (avec ou sans namespace)."""
        for child in element:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag == tag:
                return child.text
        return None

    @staticmethod
    def _parse_lastmod(lastmod: str | None) -> datetime | None:
        if not lastmod:
            return None
        try:
            return datetime.fromisoformat(lastmod.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _slug_to_title(url: str) -> str:
        """Extrait un titre lisible depuis le slug de l'URL."""
        slug = url.rstrip("/").split("/")[-1]
        slug = re.sub(r"[-_]+", " ", slug)
        return slug.strip().title()

    @classmethod
    def from_config(cls, config: dict) -> list["SitemapAgent"]:
        """Crée un SitemapAgent par catégorie depuis la section sitemap_sources du config."""
        agents = []
        sitemap_cfg = config.get("sitemap_sources", {})
        for key, value in sitemap_cfg.items():
            if key == "max_per_source" or not isinstance(value, list):
                continue
            prompt = _PROMPTS_BY_CATEGORY.get(key, "")
            agents.append(cls(key, value, config, system_prompt=prompt))
        return agents
