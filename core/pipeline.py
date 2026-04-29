"""Pipeline séquentiel : RawNewsItem → résumé → image → audio → DB."""

from __future__ import annotations

from datetime import date, datetime, timezone

from core.logger import get_logger
from core.models import (
    AgentRun,
    DailyFeed,
    NewsItem,
    RawNewsItem,
    get_session,
    init_db,
)
from processors.image_extractor import ImageExtractor
from processors.summarizer import Summarizer
from processors.tts_generator import TTSGenerator


class Pipeline:
    """Enchaîne les processeurs et persiste les résultats en DB."""

    def __init__(self, config: dict) -> None:
        self._config = config
        self._log = get_logger("core.pipeline", config.get("logging"))
        self._summarizer = Summarizer(config)
        self._image_extractor = ImageExtractor(config)
        self._tts = TTSGenerator(config)

        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        from core.models import Base

        db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def run(self, raw_items: list[RawNewsItem]) -> list[NewsItem]:
        """Traite une liste de RawNewsItem et retourne les NewsItem sauvegardés."""
        if not raw_items:
            self._log.warning("Pipeline lancé avec liste vide")
            return []

        self._log.info("Pipeline démarré", extra={"items": len(raw_items)})

        items = self._summarizer.process(raw_items)
        self._log.info("Résumés générés", extra={"items": len(items)})

        items = self._image_extractor.process(items)
        self._log.info("Images extraites", extra={"items": len(items)})

        items = self._tts.process(items)
        self._log.info("Audio généré", extra={"items": len(items)})

        news_items = self._save_to_db(items)
        self._log.info("Pipeline terminé", extra={"saved": len(news_items)})
        return news_items

    def _save_to_db(self, raw_items: list[RawNewsItem]) -> list[NewsItem]:
        session = get_session(self._session_factory)
        saved: list[NewsItem] = []
        try:
            for raw in raw_items:
                # Ignorer si déjà en DB (déduplication par URL)
                existing = (
                    session.query(NewsItem)
                    .filter_by(source_url=raw.source_url)
                    .first()
                )
                if existing:
                    saved.append(existing)
                    continue

                item = NewsItem(
                    title=raw.title,
                    source_url=raw.source_url,
                    source_name=raw.source_name,
                    category=raw.category,
                    published_at=raw.published_at,
                    description=raw.description,
                    image_url=raw.image_url,
                    video_url=raw.video_url,
                    video_type=raw.video_type,
                    raw_content=raw.raw_content,
                    popularity_score=raw.popularity_score,
                    summary_fr=raw.summary_fr,
                    image_path=raw.image_path,
                    audio_path=raw.audio_path,
                    final_score=raw.final_score,
                )
                session.add(item)
                saved.append(item)

            session.commit()
            self._create_daily_feed(session, saved)
            session.commit()
            # Détacher les instances avant fermeture pour éviter DetachedInstanceError
            session.expunge_all()
        except Exception as exc:
            session.rollback()
            self._log.error("Erreur sauvegarde DB", extra={"error": str(exc)})
            raise
        finally:
            session.close()

        return saved

    def _create_daily_feed(self, session, items: list[NewsItem]) -> None:
        today = date.today().isoformat()
        feed = session.query(DailyFeed).filter_by(date=today).first()
        item_ids = [item.id for item in items if item.id]

        import json
        if feed:
            feed.item_count = len(item_ids)
            feed.item_ids = json.dumps(item_ids)
            feed.status = "ready"
            feed.updated_at = datetime.now(timezone.utc)
        else:
            session.add(
                DailyFeed(
                    date=today,
                    status="ready",
                    item_count=len(item_ids),
                    item_ids=json.dumps(item_ids),
                )
            )
