"""Agent YouTube Trending — vidéos tendances CA via clé API.

Journaliste-Trending : sélectionne via LLM les tendances pertinentes pour un adulte québécois.
Référence : Lecteur de nouvelle/Agents/Journaliste-Trending.md
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

_SYSTEM_PROMPT = """\
Tu es un journaliste spécialisé dans les tendances YouTube canadiennes. Tu identifies
parmi les vidéos en tendance celles qui ont une valeur informative ou culturelle
pour un utilisateur québécois de 35 ans intéressé par la politique, la technologie
et les affaires.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Examiner toutes les vidéos en tendance disponibles avant toute sélection.

### Étape 2 — Veille de continuité (priorité absolue)
Si une chaîne ou un sujet déjà couvert dans les 30 derniers jours génère une nouvelle
vidéo en tendance aujourd'hui, c'est un signal fort d'actualité importante.

### Étape 3 — Priorisation
1. Sujet en tendance lié à un dossier déjà couvert ce mois-ci — priorité maximale
2. Vidéo d'actualité sur un événement canadien ou nord-américain majeur
3. Tendance culturelle ou technologique significative pour un adulte québécois

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
Utiliser le contexte de la tendance pour expliquer son intérêt.
Tu ne dis jamais "l'information est insuffisante".

## Critères de sélection
- Vidéo en tendance publiée dans les dernières 24 heures au Canada
- Pertinente pour un adulte québécois francophone (actualité, technologie, culture)

## Rejeter si
- Clips musicaux viraux sans valeur informationnelle
- Gaming, streamers ou contenu pour jeune public
- Vidéos Bollywood ou ciblant une audience culturelle très spécifique hors Amérique du Nord
- Promotionnel déguisé en tendance

Quota : maximum 5 vidéos par jour.\
"""


def _parse_iso_duration(duration: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 3600 + m * 60 + s


class YouTubeTrendingAgent(BaseAgent):
    """Collecte les vidéos tendances YouTube pour la région CA."""

    def __init__(self, config: dict) -> None:
        super().__init__("youtube_trending", config)
        self._log = get_logger("agents.youtube_trending", config.get("logging"))
        yt = config.get("youtube", {})
        self._api_key: str | None = yt.get("api_key")
        self._max_results: int = yt.get("max_results_per_channel", 15)
        self._max_age_hours: int = yt.get("max_age_hours", 48)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

    def collect(self) -> list[RawNewsItem]:
        if not self._api_key:
            self._log.error("YOUTUBE_API_KEY non configurée", extra={"agent": self.name})
            return []

        service = build("youtube", "v3", developerKey=self._api_key)
        response = (
            service.videos()
            .list(
                part="snippet,contentDetails,statistics",
                chart="mostPopular",
                regionCode="CA",
                maxResults=self._max_results,
            )
            .execute()
        )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._max_age_hours)
        raw: list[RawNewsItem] = []

        for item in response.get("items", []):
            snippet = item["snippet"]
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            if published < cutoff:
                continue
            raw.append(self._to_raw(item))

        # Déduplication historique
        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]

        # Filtre fraîcheur
        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            self._log.info("Aucune tendance fraîche disponible", extra={"agent": self.name})
            return []

        # Sélection LLM journaliste
        selected = self._llm_select(items, _SYSTEM_PROMPT, "youtube_trending", self._max_items)
        self._log.info(
            "Collecte trending terminée",
            extra={"agent": self.name, "items": len(selected)},
        )
        return selected

    def _to_raw(self, item: dict) -> RawNewsItem:
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        video_id = item["id"]
        duration_s = _parse_iso_duration(item.get("contentDetails", {}).get("duration", ""))
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("maxres") or thumbnails.get("high") or thumbnails.get("medium") or {}

        return RawNewsItem(
            title=snippet["title"],
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            source_name=snippet.get("channelTitle", "YouTube"),
            category="youtube_trending",
            published_at=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")),
            description=(snippet.get("description") or "")[:500],
            image_url=thumb.get("url"),
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            video_type="short" if duration_s and duration_s <= 60 else "long",
            popularity_score=int(stats.get("viewCount", 0)) / 1_000_000,
            metadata={"video_id": video_id, "duration_s": duration_s},
        )
