"""Agent local Contrecoeur & Sorel-Tracy — scraping municipal + presse régionale.

Journaliste-Contrecoeur : sélectionne via LLM l'actualité locale pertinente.
Fraîcheur : 72h (local = moins fréquent, fenêtre plus large que les autres agents).
Référence : Lecteur de nouvelle/Agents/Journaliste-Contrecoeur.md
"""

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

_SYSTEM_PROMPT = """\
Tu es un journaliste spécialisé dans l'actualité locale de Contrecoeur et de la région
de Sorel-Tracy (MRC de Pierre-De Saurel). L'utilisateur habite Contrecoeur.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir l'ensemble de tes feeds et sources sur les 72 dernières heures avant toute
sélection. L'actualité locale est moins fréquente — ne rien ignorer.

### Étape 2 — Veille de continuité (priorité absolue)
Chercher si un dossier local a avancé : travaux en cours, décision municipale suivant
une consultation, développement économique annoncé. Ce type d'article est toujours
prioritaire.

### Étape 3 — Priorisation
1. Mise à jour d'un dossier local déjà couvert ce mois-ci — priorité maximale
2. Décision municipale, avis public ou travaux touchant directement Contrecoeur
3. Développement économique, événement communautaire ou alerte locale

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
L'actualité locale est souvent laconique. Toujours contextualiser :
- Quel secteur ou rue est touché
- Quelle décision ou organisme est impliqué
Tu ne dis jamais "l'information est insuffisante".

## Critères de sélection
- Concerne directement Contrecoeur, Sorel-Tracy ou la MRC de Pierre-De Saurel
- Décision municipale, travaux, avis public, événement communautaire ou développement

## Rejeter si
- Actualité générale du Québec sans lien spécifique avec la région
- Événement dans une ville sans lien local (Longueuil, Québec City, etc.)
- Communiqué vague sans contenu réel ni action concrète

Quota : maximum 5 articles par jour. Moins est normal — les actualités locales sont rares.\
"""


class LocalContrecoeurAgent(BaseAgent):
    """Collecte les nouvelles locales de Contrecoeur et Sorel-Tracy.

    Fraîcheur : 72h (spécifié dans Journaliste-Contrecoeur.md, plus large que les autres).
    """

    def __init__(self, config: dict) -> None:
        super().__init__("local_contrecoeur", config)
        self._log = get_logger("agents.local_contrecoeur", config.get("logging"))

        local_cfg = config.get("local_contrecoeur", {})
        self._max_age_hours: int = local_cfg.get("max_age_hours", 72)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

        # Sources RSS depuis config, avec fallback
        rss_feeds = local_cfg.get("rss_feeds") or [
            {"url": "https://www.journallesoir.ca/feed/", "name": "Journal Le Soir"},
            {"url": "https://www.les2rives.com/feed/", "name": "Les 2 Rives"},
            {"url": "https://lecontrecourant.ca/feed/", "name": "Le Contrecourant"},
        ]
        self._rss_agent = RSSAgent("local_contrecoeur", rss_feeds, config)

        # Sources de scraping HTML depuis config, avec fallback
        self._scrape_sources = local_cfg.get("scrape_sources") or [
            {
                "url": "https://www.contrecoeur.ca/actualites",
                "name": "Ville de Contrecoeur",
                "base_url": "https://www.contrecoeur.ca",
            },
            {
                "url": "https://ville.sorel-tracy.qc.ca/actualites",
                "name": "Ville de Sorel-Tracy",
                "base_url": "https://ville.sorel-tracy.qc.ca",
            },
        ]

    def collect(self) -> list[RawNewsItem]:
        raw: list[RawNewsItem] = []

        # 1. Feeds RSS régionaux
        try:
            raw.extend(self._rss_agent.collect())
        except Exception as exc:
            self._log.warning("RSS local échoué", extra={"agent": self.name, "error": str(exc)})

        # 2. Scraping HTML des sites municipaux
        for source in self._scrape_sources:
            try:
                scraped = self._scrape_source(source)
                raw.extend(scraped)
                self._log.info(
                    "Scraping local OK",
                    extra={"agent": self.name, "source": source["name"], "items": len(scraped)},
                )
            except Exception as exc:
                self._log.warning(
                    "Scraping local échoué",
                    extra={"agent": self.name, "source": source["name"], "error": str(exc)},
                )

        # 3. Déduplication historique
        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]

        # 4. Filtre fraîcheur (72h pour le local)
        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            self._log.info(
                "Collecte locale terminée — aucun article frais",
                extra={"agent": self.name},
            )
            return []

        # 5. Sélection LLM journaliste
        selected = self._llm_select(items, _SYSTEM_PROMPT, "local_contrecoeur", self._max_items)
        self._log.info(
            "Collecte locale terminée",
            extra={"agent": self.name, "items": len(selected)},
        )
        return selected

    def _scrape_source(self, source: dict) -> list[RawNewsItem]:
        resp = requests.get(source["url"], headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items: list[RawNewsItem] = []

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
                    published_at=datetime.now(timezone.utc),  # Date inconnue → aujourd'hui
                )
            )
            if len(items) >= 10:
                break

        return items
