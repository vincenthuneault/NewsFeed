"""Agent contenu viral — YouTube Shorts (< 60s) en tendance CA."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem


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
        items: list[RawNewsItem] = []

        for item in response.get("items", []):
            snippet = item["snippet"]
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            if published < cutoff:
                continue

            duration_s = _parse_iso_duration(item.get("contentDetails", {}).get("duration", ""))
            if duration_s > 60:  # Garder seulement les Shorts
                continue

            items.append(self._to_raw(item, duration_s))

        self._log.info(
            "Collecte viral terminée",
            extra={"agent": self.name, "shorts": len(items)},
        )
        return items

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
