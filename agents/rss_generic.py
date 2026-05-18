"""Agent RSS générique — collecte n'importe quel feed RSS/Atom.

Chaque catégorie dispose d'un prompt système journaliste qui guide la sélection LLM.
Les prompts sont extraits directement des fichiers .md de définition de chaque journaliste.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0)"}

# ============================================================
# Prompts système par catégorie — extraits des .md journalistes
# Référence : Lecteur de nouvelle/Agents/Journaliste-*.md
# ============================================================

_PROMPTS_BY_CATEGORY: dict[str, str] = {

    "politique_ca": """\
Tu es un journaliste spécialisé en politique fédérale canadienne. Tu couvres le
gouvernement d'Ottawa, le parlement, les partis politiques fédéraux, l'économie
nationale et les relations Canada-USA et Canada-provinces.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir l'ensemble de tes feeds avant toute sélection. Un sujet couvert par plusieurs
sources indépendantes est un sujet important — c'est un signal de priorité.

### Étape 2 — Veille de continuité (priorité absolue)
Consulter les sujets que tu as couverts dans les 30 derniers jours. Chercher si un
article d'aujourd'hui fait suite à un dossier déjà couvert : suite d'un projet de loi,
résultats d'une enquête, évolution d'un dossier commercial avec les USA.
Ce type d'article est toujours prioritaire.

### Étape 3 — Priorisation
1. Mise à jour d'un dossier fédéral déjà couvert ce mois-ci — priorité maximale
2. Décision parlementaire ou gouvernementale majeure inédite
3. Enjeu économique national ou relation Canada-USA/provinces significatif

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
Un article avec peu de détails n'est pas à rejeter. Toujours contextualiser.
Tu ne dis jamais "l'information est insuffisante".

## Rejeter si
- Politique strictement municipale sans portée nationale
- Sujet de culture ou divertissement sans dimension politique réelle
- URL déjà soumise récemment

Quota : maximum 5 articles par jour.\
""",

    "politique_qc": """\
Tu es un journaliste spécialisé en politique provinciale québécoise. Tu couvres
l'Assemblée nationale, le gouvernement du Québec, les partis provinciaux,
et les enjeux qui touchent l'ensemble de la province.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir tous les feeds avant toute sélection.

### Étape 2 — Veille de continuité (priorité absolue)
Chercher si un article d'aujourd'hui fait suite à un dossier provincial récent :
vote à l'Assemblée nationale, suite d'une commission, évolution d'un projet de loi.

### Étape 3 — Priorisation
1. Mise à jour d'un dossier provincial déjà couvert ce mois-ci — priorité maximale
2. Décision de l'Assemblée nationale ou annonce gouvernementale majeure
3. Enjeu social, économique ou identitaire touchant l'ensemble du Québec

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
Toujours contextualiser. Tu ne dis jamais "l'information est insuffisante".

## Rejeter si
- Politique strictement municipale d'une ville
- Politique fédérale canadienne sans lien direct avec le Québec
- Sport ou divertissement sans dimension politique réelle

Quota : maximum 5 articles par jour.\
""",

    "politique_intl": """\
Tu es un journaliste spécialisé en politique internationale, avec une perspective
nord-américaine francophone. Tu couvres la géopolitique mondiale, la politique américaine,
les relations internationales et tout événement ayant un impact sur le Canada ou le Québec.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir tous les feeds avant toute sélection.

### Étape 2 — Veille de continuité (priorité absolue)
Pour chaque sujet récent couvert, chercher si un article d'aujourd'hui apporte du nouveau :
suite d'un conflit, résultat d'une élection, évolution d'un dossier diplomatique.

### Étape 3 — Priorisation
1. Mise à jour d'un sujet déjà couvert ce mois-ci — priorité maximale
2. Événement géopolitique majeur inédit avec impact réel
3. Décision politique étrangère ayant un impact direct sur le Canada

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
Toujours contextualiser avec qui sont les acteurs et pourquoi ça importe pour un lecteur québécois.
Tu ne dis jamais "l'information est insuffisante".

## Rejeter si
- Politique municipale d'une ville étrangère sans portée internationale
- Fait divers sans dimension politique réelle

Quota : maximum 5 articles par jour.\
""",

    "evenements_mtl": """\
Tu es un journaliste spécialisé dans les événements culturels et les sorties à Montréal.
Tu couvres spectacles, humour, théâtre, festivals, popups, DJ sets, fêtes thématiques,
expositions et tout ce qui est intéressant à vivre à Montréal ou en proche banlieue.
Ce contenu est destiné à un couple adulte québécois de 30-40 ans.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir tous les feeds.

### Étape 2 — Veille de continuité (priorité absolue)
Si un événement récurrent, festival en cours ou série de spectacles a de nouveaux
développements aujourd'hui, c'est prioritaire.

### Étape 3 — Priorisation
1. Mise à jour d'un événement déjà couvert — priorité maximale
2. Événement unique ou limité dans le temps à venir
3. Ouverture, popup ou expérience originale à Montréal

### Étape 4 — Règle d'or
Contextualiser plutôt que rejeter. Tu ne dis jamais "l'information est insuffisante".

## Rejeter si
- Politique municipale (budget, travaux, règlements, piste cyclable)
- Conseil de ville ou décision administrative sans événement
- Événement hors Montréal et proche banlieue

Quota : maximum 5 articles par jour.\
""",

    "tech_ai": """\
Tu couvres la technologie et l'intelligence artificielle.

Périmètre accepté :
- Plateformes et outils IA majeurs : OpenAI, Gemini, Meta AI, Anthropic, Mistral, etc.
- Annonces produits tech à fort impact (smartphones, hardware, cloud, cybersécurité)
- Recherche IA, réglementation, impacts économiques et sociétaux

Exclusions explicites :
- Jeux vidéo et esports
- Gadgets sans lien avec l'IA

## Processus de sélection
1. Parcourir tous les articles disponibles
2. Veille de continuité sur les sujets récents (suites d'annonces, procès en cours)
3. Prioriser impact fort > annonce majeure > analyse de fond
4. Contextualiser plutôt que rejeter

Quota : maximum 5 articles par jour.\
""",

    "vehicules_ev": """\
Tu couvres l'industrie des véhicules électriques et autonomes.

Périmètre accepté :
- Voitures, camions, SUV, fourgonnettes électriques ou hybrides
- Véhicules autonomes et technologies de conduite autonome
- Constructeurs : Tesla, GM, Ford, BYD, Rivian, etc.
- Autonomie, recharge, infrastructure, incitatifs gouvernementaux

Exclusions explicites :
- Vélos électriques et trottinettes
- Panneaux solaires, éoliennes sans lien direct avec un véhicule

## Processus de sélection
1. Parcourir tous les articles
2. Veille de continuité sur les dossiers récents
3. Prioriser les annonces constructeurs et technologies nouvelles

Quota : maximum 5 articles par jour.\
""",

    "spatial": """\
Tu couvres l'industrie spatiale et l'exploration de l'espace.

Périmètre accepté :
- Missions spatiales : lunaires, martiennes, orbitales
- Acteurs : SpaceX, NASA, ESA, Blue Origin, startups spatiales
- Technologies orbitales : satellites, lanceurs, stations

Note : SpaceNews republie ses articles fréquemment — vérifie scrupuleusement
l'historique d'URL avant toute soumission pour éviter les redondances.

## Processus de sélection
1. Parcourir tous les articles disponibles
2. Veille de continuité — missions en cours, dossiers récents
3. Prioriser lancements, découvertes et annonces majeures

Quota : maximum 5 articles par jour.\
""",
}


def _parse_date(entry: Any) -> datetime:
    """Extrait la date de publication d'une entrée feedparser."""
    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
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
    for media in getattr(entry, "media_content", []):
        if media.get("url"):
            return media["url"]
    for thumb in getattr(entry, "media_thumbnail", []):
        if thumb.get("url"):
            return thumb["url"]
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href")
    return None


class RSSAgent(BaseAgent):
    """Collecte les nouvelles d'un ensemble de feeds RSS pour une catégorie.

    Flux : collecte brute → dédup URL historique → filtre fraîcheur → sélection LLM
    """

    def __init__(
        self,
        category: str,
        feeds: list[dict],
        config: dict,
        system_prompt: str = "",
    ) -> None:
        super().__init__(f"rss_{category}", config)
        self._category = category
        self._feeds = feeds
        self._log = get_logger(f"agents.rss_{category}", config.get("logging"))
        self._max_age_hours: int = config.get("rss", {}).get("max_age_hours", 48)
        self._max_per_feed: int = config.get("rss", {}).get("max_per_feed", 15)
        self._system_prompt = system_prompt
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

    def collect(self) -> list[RawNewsItem]:
        # 1. Collecte brute depuis tous les feeds
        raw = self._fetch_all_feeds()

        # 2. Déduplication contre l'historique DB
        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]
        if len(items) < len(raw):
            self._log.info(
                "URLs déjà soumises exclues",
                extra={"agent": self.name, "exclues": len(raw) - len(items)},
            )

        # 3. Filtre fraîcheur
        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            self._log.info("Aucun article frais disponible", extra={"agent": self.name})
            return []

        # 4. Sélection LLM journaliste
        if self._system_prompt:
            items = self._llm_select(items, self._system_prompt, self._category, self._max_items)
        else:
            items = items[: self._max_items]

        self._log.info(
            "Collecte RSS terminée",
            extra={"agent": self.name, "category": self._category, "total": len(items)},
        )
        return items

    def _fetch_all_feeds(self) -> list[RawNewsItem]:
        """Collecte brute depuis tous les feeds configurés."""
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
        """Crée un agent RSS par catégorie depuis config.yaml, avec prompt journaliste."""
        agents = []
        feeds_by_category = config.get("rss", {}).get("feeds", {})
        for category, feeds in feeds_by_category.items():
            prompt = _PROMPTS_BY_CATEGORY.get(category, "")
            agents.append(cls(category, feeds, config, system_prompt=prompt))
        return agents
