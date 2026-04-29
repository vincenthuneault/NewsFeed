"""Processeur de scoring — calcule final_score et sélectionne le top 30."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from core.logger import get_logger
from core.models import Feedback, NewsItem, RawNewsItem, get_session, init_db
from processors.base_processor import BaseProcessor

# Fiabilité par source (1.0 = très fiable, 0.5 = neutre)
_RELIABILITY: dict[str, float] = {
    "RC Montréal": 0.95,
    "RC Arts & culture": 0.90,
    "RC Grand Montréal": 0.95,
    "Radio-Canada Politique": 0.95,
    "Radio-Canada Québec": 0.95,
    "Ars Technica": 0.90,
    "The Verge": 0.85,
    "SpaceNews": 0.90,
    "Electrek": 0.80,
    "YouTube": 0.60,
}
_DEFAULT_RELIABILITY = 0.65
_FEEDBACK_DECAY_DAYS = 30


class Scorer(BaseProcessor):
    """Assigne un final_score à chaque item et sélectionne le top N."""

    def __init__(self, config: dict) -> None:
        super().__init__("scorer", config)
        self._log = get_logger("processors.scorer", config.get("logging"))
        scoring = config.get("scoring", {})
        weights = scoring.get("weights", {})
        self._w_freshness: float = weights.get("freshness", 0.30)
        self._w_reliability: float = weights.get("reliability", 0.25)
        self._w_diversity: float = weights.get("diversity", 0.20)
        self._w_feedback: float = weights.get("feedback", 0.25)
        self._max_category_ratio: float = scoring.get("max_category_ratio", 0.40)
        self._decay_hours: float = scoring.get("freshness_decay_hours", 48)
        self._max_items: int = config.get("app", {}).get("max_feed_items", 30)

        db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
        self._session_factory = init_db(db_url)

    def process(self, items: list) -> list:
        if not items:
            return []

        now = datetime.now(timezone.utc)
        category_boosts = self._load_category_boosts()

        if category_boosts:
            self._log.info(
                "Boosts feedback actifs",
                extra={"boosts": {k: round(v, 3) for k, v in category_boosts.items()}},
            )

        for item in items:
            item.final_score = self._compute_score(item, now, category_boosts)

        items.sort(key=lambda x: x.final_score, reverse=True)
        selected = self._select_with_diversity(items)

        self._log.info(
            "Scoring terminé",
            extra={
                "candidats": len(items),
                "sélectionnés": len(selected),
                "distribution": self._category_distribution(selected),
            },
        )
        return selected

    def _load_category_boosts(self) -> dict[str, float]:
        """Charge les boosts par catégorie depuis l'historique de feedback.

        Retourne un dict catégorie → boost ∈ [-1, +1].
        Un boost positif = la catégorie est souvent aimée.
        """
        session = get_session(self._session_factory)
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=_FEEDBACK_DECAY_DAYS)
            rows = (
                session.query(Feedback.action, Feedback.created_at, NewsItem.category)
                .join(NewsItem, Feedback.news_item_id == NewsItem.id)
                .filter(Feedback.created_at >= cutoff)
                .filter(Feedback.action.in_(["like", "dislike"]))
                .all()
            )
        except Exception as exc:
            self._log.warning("Chargement feedback échoué", extra={"error": str(exc)})
            return {}
        finally:
            session.close()

        # Agréger par catégorie avec décroissance temporelle
        category_scores: dict[str, list[float]] = {}
        now = datetime.now(timezone.utc)
        for action, created_at, category in rows:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_days = max(0, (now - created_at).total_seconds() / 86400)
            decay = math.exp(-age_days / _FEEDBACK_DECAY_DAYS)
            value = (1.0 if action == "like" else -1.0) * decay
            category_scores.setdefault(category, []).append(value)

        return {
            cat: max(-1.0, min(1.0, sum(vals) / len(vals)))
            for cat, vals in category_scores.items()
        }

    def _compute_score(
        self, item: RawNewsItem, now: datetime, boosts: dict[str, float]
    ) -> float:
        freshness = self._freshness_score(item.published_at, now)
        reliability = _RELIABILITY.get(item.source_name, _DEFAULT_RELIABILITY)
        popularity = min(item.popularity_score / 10.0, 1.0)

        # Feedback : boost normalisé en [0, 1] (0.5 = neutre)
        raw_boost = boosts.get(item.category, 0.0)
        feedback_score = 0.5 + raw_boost * 0.5  # [-1,1] → [0, 1]

        score = (
            self._w_freshness * freshness
            + self._w_reliability * reliability
            + self._w_diversity * popularity
            + self._w_feedback * feedback_score
        )
        return round(score, 4)

    def _freshness_score(self, published_at: datetime, now: datetime) -> float:
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (now - published_at).total_seconds() / 3600)
        k = 1.5 / max(self._decay_hours, 1)
        return math.exp(-k * age_hours)

    def _select_with_diversity(self, sorted_items: list[RawNewsItem]) -> list[RawNewsItem]:
        max_per_category = max(1, int(self._max_items * self._max_category_ratio))
        category_counts: dict[str, int] = {}
        selected: list[RawNewsItem] = []

        for item in sorted_items:
            if len(selected) >= self._max_items:
                break
            count = category_counts.get(item.category, 0)
            if count >= max_per_category:
                continue
            category_counts[item.category] = count + 1
            selected.append(item)

        return selected

    def _category_distribution(self, items: list[RawNewsItem]) -> dict[str, int]:
        dist: dict[str, int] = {}
        for item in items:
            dist[item.category] = dist.get(item.category, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: -x[1]))
