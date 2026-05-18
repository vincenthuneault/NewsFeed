"""Agent YouTube — abonnements (OAuth 2.0) avec fallback tendances CA.

Journaliste-YoutubeSub : sélectionne via LLM les vidéos pertinentes des chaînes abonnées.
Référence : Lecteur de nouvelle/Agents/Journaliste-YoutubeSub.md
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OAUTH_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

_SYSTEM_PROMPT = """\
Tu es un journaliste de veille spécialisé dans les chaînes YouTube auxquelles
l'utilisateur est abonné. L'utilisateur s'intéresse à la politique, la technologie,
les affaires (business), la science et l'actualité nord-américaine.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir toutes les vidéos publiées aujourd'hui par les chaînes abonnées avant toute
sélection. Une chaîne qui couvre le même sujet qu'une autre signale un sujet important.

### Étape 2 — Veille de continuité (priorité absolue)
Chercher si une chaîne publie aujourd'hui une suite ou mise à jour d'un sujet déjà
présenté dans les 30 derniers jours. Ce type de vidéo est toujours prioritaire.

### Étape 3 — Priorisation
1. Mise à jour ou suite d'un sujet déjà couvert ce mois-ci — priorité maximale
2. Vidéo sur un événement d'actualité important publiée aujourd'hui
3. Analyse ou contenu de fond pertinent sur un sujet d'intérêt

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
Si la description est vague, contextualiser avec le sujet habituel de la chaîne.
Tu ne dis jamais "l'information est insuffisante".

## Critères de sélection
- Vidéo publiée dans les dernières 24 heures par une chaîne abonnée
- Contenu informatif, analytique ou de fond sur la politique, la tech ou les affaires

## Rejeter si
- Contenu de gaming, clips musicaux ou variétés sans valeur informationnelle
- Vidéo promotionnelle sans contenu substantiel
- Contenu ciblant un jeune public

Quota : maximum 5 vidéos par jour.\
"""


def _parse_iso_duration(duration: str) -> int:
    """Convertit une durée ISO 8601 (ex: PT4M13S) en secondes."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 3600 + m * 60 + s


class YouTubeSubsAgent(BaseAgent):
    """Collecte les vidéos des abonnements YouTube (OAuth 2.0).

    Fallback automatique vers les tendances CA si youtube_oauth.json absent.
    """

    def __init__(self, config: dict) -> None:
        super().__init__("youtube_subs", config)
        self._log = get_logger("agents.youtube_subs", config.get("logging"))
        yt = config.get("youtube", {})
        self._api_key: str | None = yt.get("api_key")
        self._max_results: int = yt.get("max_results_per_channel", 10)
        self._max_age_hours: int = yt.get("max_age_hours", 48)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

    def collect(self) -> list[RawNewsItem]:
        oauth_path = PROJECT_ROOT / "secrets" / "youtube_oauth.json"
        if oauth_path.exists():
            try:
                raw = self._collect_subscriptions(oauth_path)
            except Exception as exc:
                self._log.warning(
                    "OAuth échoué, fallback tendances",
                    extra={"agent": self.name, "error": str(exc)},
                )
                raw = self._collect_trending() if self._api_key else []
        elif self._api_key:
            raw = self._collect_trending()
        else:
            self._log.error("Ni OAuth ni API key configurés", extra={"agent": self.name})
            return []

        # Déduplication historique
        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]

        # Filtre fraîcheur
        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            return []

        # Sélection LLM journaliste
        return self._llm_select(items, _SYSTEM_PROMPT, "youtube_subs", self._max_items)

    # ------------------------------------------------------------------
    # OAuth — abonnements
    # ------------------------------------------------------------------

    def _build_oauth_service(self, oauth_path: Path):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        token_path = PROJECT_ROOT / "secrets" / "youtube_token.json"
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), OAUTH_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(oauth_path), OAUTH_SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=creds)

    def _collect_subscriptions(self, oauth_path: Path) -> list[RawNewsItem]:
        service = self._build_oauth_service(oauth_path)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._max_age_hours)
        channel_ids = self._get_subscription_channel_ids(service)
        self._log.info(
            "Abonnements récupérés",
            extra={"agent": self.name, "channels": len(channel_ids)},
        )

        items: list[RawNewsItem] = []
        for channel_id in channel_ids:
            items.extend(self._get_channel_videos(service, channel_id, cutoff))
            if len(items) >= 50:
                break

        return items

    def _get_subscription_channel_ids(self, service) -> list[str]:
        ids: list[str] = []
        request = service.subscriptions().list(
            part="snippet", mine=True, maxResults=50, order="relevance"
        )
        while request:
            response = request.execute()
            for item in response.get("items", []):
                ids.append(item["snippet"]["resourceId"]["channelId"])
            request = service.subscriptions().list_next(request, response)
        return ids

    def _get_channel_videos(
        self, service, channel_id: str, cutoff: datetime
    ) -> list[RawNewsItem]:
        response = (
            service.search()
            .list(
                part="snippet",
                channelId=channel_id,
                type="video",
                order="date",
                maxResults=self._max_results,
                publishedAfter=cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            .execute()
        )

        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        if not video_ids:
            return []

        details = (
            service.videos()
            .list(part="snippet,contentDetails,statistics", id=",".join(video_ids))
            .execute()
        )

        return [self._video_to_raw(item) for item in details.get("items", [])]

    # ------------------------------------------------------------------
    # API key — tendances (fallback)
    # ------------------------------------------------------------------

    def _collect_trending(self) -> list[RawNewsItem]:
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
        items = []
        for item in response.get("items", []):
            published = datetime.fromisoformat(
                item["snippet"]["publishedAt"].replace("Z", "+00:00")
            )
            if published < cutoff:
                continue
            items.append(self._video_to_raw(item))

        return items

    # ------------------------------------------------------------------
    # Conversion commune
    # ------------------------------------------------------------------

    def _video_to_raw(self, item: dict) -> RawNewsItem:
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        video_id = item["id"]
        duration_s = _parse_iso_duration(
            item.get("contentDetails", {}).get("duration", "")
        )
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("maxres")
            or thumbnails.get("high")
            or thumbnails.get("medium")
            or {}
        )
        return RawNewsItem(
            title=snippet["title"],
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            source_name=snippet.get("channelTitle", "YouTube"),
            category="youtube_subs",
            published_at=datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            ),
            description=(snippet.get("description") or "")[:500],
            image_url=thumbnail.get("url"),
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            video_type="short" if duration_s and duration_s <= 60 else "long",
            popularity_score=int(stats.get("viewCount", 0)) / 1_000_000,
            metadata={"video_id": video_id, "duration_s": duration_s},
        )
