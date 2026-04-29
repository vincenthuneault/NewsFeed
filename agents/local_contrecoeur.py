"""Agent local Contrecoeur & Sorel-Tracy — scraping municipal + presse régionale."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from agents.base_agent import BaseAgent
from agents.rss_generic import RSSAgent
from core.logger import get_logger
from core.models import RawNewsItem

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0)"}
_TIMEOUT = 15

# Feeds RSS régionaux disponibles publiquement
_RSS_FEEDS = [
    {"url": "https://www.journallesoir.ca/feed/", "name": "Journal Le Soir"},
    {"url": "https://soreltraci.com/feed/", "name": "Sorel-Tracy"},
]

# Pages HTML à scraper comme fallback
_SCRAPE_SOURCES = [
    {
        "url": "https://www.contrecoeur.ca/actualites",
        "name": "Contrecoeur",
        "base_url": "https://www.contrecoeur.ca",
    },
]


class LocalContrecoeurAgent(BaseAgent):
    """Collecte les nouvelles locales de Contrecoeur et Sorel-Tracy."""

    def __init__(self, config: dict) -> None:
        super().__init__("local_contrecoeur", config)
        self._log = get_logger("agents.local_contrecoeur", config.get("logging"))
        self._max_age_hours: int = config.get("rss", {}).get("max_age_hours", 72)
        self._rss_agent = RSSAgent("local_contrecoeur", _RSS_FEEDS, config)

    def collect(self) -> list[RawNewsItem]:
        items: list[RawNewsItem] = []

        # 1. Feeds RSS régionaux
        try:
            items.extend(self._rss_agent.collect())
        except Exception as exc:
            self._log.warning("RSS local échoué", extra={"agent": self.name, "error": str(exc)})

        # 2. Scraping HTML des sites municipaux
        for source in _SCRAPE_SOURCES:
            try:
                scraped = self._scrape_source(source)
                items.extend(scraped)
                self._log.info(
                    "Scraping local OK",
                    extra={"agent": self.name, "source": source["name"], "items": len(scraped)},
                )
            except Exception as exc:
                self._log.warning(
                    "Scraping local échoué",
                    extra={"agent": self.name, "source": source["name"], "error": str(exc)},
                )

        self._log.info(
            "Collecte locale terminée",
            extra={"agent": self.name, "items": len(items)},
        )
        return items

    def _scrape_source(self, source: dict) -> list[RawNewsItem]:
        resp = requests.get(source["url"], headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._max_age_hours)
        items: list[RawNewsItem] = []

        # Chercher des articles génériques (h2/h3 avec lien)
        for tag in soup.find_all(["article", "li"], class_=re.compile(r"(news|article|post|actu)", re.I)):
            link_tag = tag.find("a", href=True)
            title_tag = tag.find(["h2", "h3", "h4"])
            if not link_tag or not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = link_tag["href"]
            if not href.startswith("http"):
                href = source["base_url"] + href

            if not title or not href:
                continue

            items.append(
                RawNewsItem(
                    title=title,
                    source_url=href,
                    source_name=source["name"],
                    category="local_contrecoeur",
                    published_at=datetime.now(timezone.utc),
                )
            )
            if len(items) >= 10:
                break

        return items
