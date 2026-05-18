"""Agent contenu viral — YouTube Shorts (< 60s) en tendance CA.

Journaliste-ShortsTrending : sélectionne via LLM les Shorts viraux partageables.
Référence : Lecteur de nouvelle/Agents/Journaliste-ShortsTrending.md
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

_SYSTEM_PROMPT = """\
Tu es un journaliste spécialisé dans le contenu viral court sur YouTube.
Tu identifies parmi les Shorts en tendance ceux qui valent la peine d'être partagés :
drôles, surprenants, émouvants ou culturellement pertinents.

Ce contenu est destiné à être partagé, notamment en couple. L'utilisateur aime
la musique électronique/EDM/techno et apprécierait des surprises culturelles.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Examiner tous les Shorts en tendance disponibles avant toute sélection.

### Étape 2 — Veille de continuité (priorité absolue)
Si un créateur ou format récurrent génère un nouveau Short viral aujourd'hui,
c'est souvent un signe de qualité constante. Priorité sur les nouvelles découvertes.

### Étape 3 — Priorisation
1. Suite ou série d'un créateur déjà sélectionné ce mois-ci — priorité maximale
2. Short drôle, surprenant ou émotionnellement fort avec large portée
3. Tendance culturelle légère intéressante pour un couple québécois adulte

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
Si la description est vague, contextualiser avec le potentiel de partage.
Tu ne dis jamais "l'information est insuffisante".

## Critères de sélection
- Short publié dans les dernières 24 heures, durée ≤ 60 secondes
- Contenu divertissant, surprenant, drôle ou culturellement intéressant

## Rejeter si
- Clips musicaux d'artistes hip-hop ou rap peu connus du public général
- Gaming ou streamers sans intérêt général
- Contenu Bollywood ou K-pop
- Vidéo promotionnelle déguisée en contenu viral

Quota : maximum 5 vidéos par jour.\
"""


def _parse_iso_duration(duration: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 3600 + m * 60 + s


class ViralTrendingAgent(BaseAgent):
    """Collecte les YouTube Shorts viraux (durée ≤ 60s) tendances CA."""

    def __init__(self, config: dict) -> None:
        super().__init__("viral_trending", config)
        self._log = get_logger("agents.viral_trending", config.get("logging"))
        yt = config.get("youtube", {})
        self._api_key: str | None = yt.get("api_key")
        self._max_results: int = 25  # Récupère plus pour filtrer les Shorts
        self._max_age_hours: int = yt.get("max_age_hours", 48)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

    def collect(self) -> list[RawNewsItem]:
        if not self._api_key:
            self._log.error("YOUTUBE_API_KEY manquante", extra={"agent": self.name})
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

            duration_s = _parse_iso_duration(item.get("contentDetails", {}).get("duration", ""))
            if duration_s > 60:  # Garder seulement les Shorts
                continue

            raw.append(self._to_raw(item, duration_s))

        # Déduplication historique
        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]

        # Filtre fraîcheur
        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            self._log.info("Aucun Short frais disponible", extra={"agent": self.name})
            return []

        # Sélection LLM journaliste
        selected = self._llm_select(items, _SYSTEM_PROMPT, "viral", self._max_items)
        self._log.info(
            "Collecte viral terminée",
            extra={"agent": self.name, "shorts": len(selected)},
        )
        return selected

    def _to_raw(self, item: dict, duration_s: int) -> RawNewsItem:
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        video_id = item["id"]
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("maxres") or thumbnails.get("high") or thumbnails.get("medium") or {}

        return RawNewsItem(
            title=snippet["title"],
            source_url=f"https://www.youtube.com/shorts/{video_id}",
            source_name=snippet.get("channelTitle", "YouTube"),
            category="viral",
            published_at=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")),
            description=(snippet.get("description") or "")[:300],
            image_url=thumb.get("url"),
            video_url=f"https://www.youtube.com/shorts/{video_id}",
            video_type="short",
            popularity_score=int(stats.get("viewCount", 0)) / 1_000_000,
            metadata={"video_id": video_id, "duration_s": duration_s},
        )
