"""Tests unitaires — Modèles de données."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.models import (
    CATEGORIES,
    AgentRun,
    Base,
    DailyFeed,
    Feedback,
    NewsItem,
    RawNewsItem,
    get_session,
    init_db,
)


@pytest.fixture
def session():
    """Session SQLAlchemy en mémoire, tables créées."""
    SessionFactory = init_db("sqlite:///:memory:", echo=False)
    session = get_session(SessionFactory)
    yield session
    session.close()


# ============================================================
# RawNewsItem (dataclass)
# ============================================================


class TestRawNewsItem:
    """Tests pour la dataclass RawNewsItem."""

    def test_creation_minimale(self) -> None:
        item = RawNewsItem(
            title="Test",
            source_url="https://example.com",
            source_name="Example",
            category="tech_ai",
            published_at=datetime.now(timezone.utc),
        )
        assert item.title == "Test"
        assert item.description is None
        assert item.popularity_score == 0.0
        assert item.summary_fr is None
        assert item.final_score == 0.0

    def test_creation_complete(self) -> None:
        item = RawNewsItem(
            title="Nouvelle complète",
            source_url="https://example.com/article",
            source_name="Example",
            category="politique_ca",
            published_at=datetime.now(timezone.utc),
            description="Description test",
            image_url="https://example.com/img.jpg",
            video_url="https://youtube.com/watch?v=abc",
            video_type="long",
            raw_content="Contenu brut...",
            popularity_score=42.5,
            metadata={"channel_id": "UC123"},
        )
        assert item.description == "Description test"
        assert item.video_type == "long"
        assert item.metadata["channel_id"] == "UC123"

    def test_champs_pipeline_non_dans_repr(self) -> None:
        """Les champs pipeline ne doivent pas apparaître dans repr."""
        item = RawNewsItem(
            title="Test",
            source_url="https://example.com",
            source_name="Example",
            category="tech_ai",
            published_at=datetime.now(timezone.utc),
            summary_fr="Un résumé",
        )
        repr_str = repr(item)
        assert "summary_fr" not in repr_str


# ============================================================
# Catégories
# ============================================================


class TestCategories:
    """Tests pour les catégories normalisées."""

    def test_categories_attendues(self) -> None:
        expected = [
            "youtube_subs", "youtube_trending", "viral",
            "tech_ai", "politique_ca", "politique_qc",
            "evenements_mtl", "local_contrecoeur",
        ]
        for cat in expected:
            assert cat in CATEGORIES

    def test_labels_non_vides(self) -> None:
        for key, label in CATEGORIES.items():
            assert len(label) > 0


# ============================================================
# NewsItem (SQLAlchemy)
# ============================================================


class TestNewsItem:
    """CRUD sur la table news_items."""

    def _make_item(self) -> NewsItem:
        return NewsItem(
            title="Article test",
            source_url="https://example.com/unique-123",
            source_name="Test Source",
            category="tech_ai",
            published_at=datetime.now(timezone.utc),
        )

    def test_create(self, session) -> None:
        item = self._make_item()
        session.add(item)
        session.commit()
        assert item.id is not None
        assert item.created_at is not None

    def test_read(self, session) -> None:
        item = self._make_item()
        session.add(item)
        session.commit()

        found = session.query(NewsItem).filter_by(id=item.id).first()
        assert found is not None
        assert found.title == "Article test"

    def test_update(self, session) -> None:
        item = self._make_item()
        session.add(item)
        session.commit()

        item.summary_fr = "Résumé test"
        item.final_score = 0.75
        session.commit()

        found = session.query(NewsItem).get(item.id)
        assert found.summary_fr == "Résumé test"
        assert found.final_score == 0.75

    def test_delete(self, session) -> None:
        item = self._make_item()
        session.add(item)
        session.commit()
        item_id = item.id

        session.delete(item)
        session.commit()

        assert session.query(NewsItem).get(item_id) is None

    def test_source_url_unique(self, session) -> None:
        item1 = self._make_item()
        session.add(item1)
        session.commit()

        item2 = self._make_item()  # même source_url
        session.add(item2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


# ============================================================
# DailyFeed
# ============================================================


class TestDailyFeed:
    """CRUD sur la table daily_feeds."""

    def test_create_feed(self, session) -> None:
        feed = DailyFeed(
            date="2026-04-18",
            status="ready",
            item_count=25,
            item_ids=json.dumps([1, 2, 3, 4, 5]),
        )
        session.add(feed)
        session.commit()
        assert feed.id is not None

    def test_date_unique(self, session) -> None:
        feed1 = DailyFeed(date="2026-04-18", status="ready")
        session.add(feed1)
        session.commit()

        feed2 = DailyFeed(date="2026-04-18", status="failed")
        session.add(feed2)
        with pytest.raises(Exception):
            session.commit()


# ============================================================
# Feedback
# ============================================================


class TestFeedback:
    """CRUD sur la table feedbacks."""

    def test_create_feedback(self, session) -> None:
        item = NewsItem(
            title="Article feedback",
            source_url="https://example.com/fb-1",
            source_name="Test",
            category="tech_ai",
            published_at=datetime.now(timezone.utc),
        )
        session.add(item)
        session.commit()

        fb = Feedback(news_item_id=item.id, action="like")
        session.add(fb)
        session.commit()
        assert fb.id is not None

    def test_cascade_delete(self, session) -> None:
        """Supprimer un NewsItem supprime ses feedbacks."""
        item = NewsItem(
            title="Article cascade",
            source_url="https://example.com/cascade-1",
            source_name="Test",
            category="tech_ai",
            published_at=datetime.now(timezone.utc),
        )
        session.add(item)
        session.commit()

        fb = Feedback(news_item_id=item.id, action="dislike", comment="pas pertinent")
        session.add(fb)
        session.commit()

        session.delete(item)
        session.commit()
        assert session.query(Feedback).count() == 0


# ============================================================
# AgentRun
# ============================================================


class TestAgentRun:
    """CRUD sur la table agent_runs."""

    def test_create_run(self, session) -> None:
        run = AgentRun(
            agent_name="youtube_subs",
            status="success",
            items_collected=15,
            duration_seconds=12.5,
        )
        session.add(run)
        session.commit()
        assert run.id is not None

    def test_run_avec_erreur(self, session) -> None:
        run = AgentRun(
            agent_name="rss_generic",
            status="failed",
            items_collected=0,
            error_message="Connection timeout",
        )
        session.add(run)
        session.commit()
        assert run.error_message == "Connection timeout"
